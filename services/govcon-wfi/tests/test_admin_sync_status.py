"""Sync-status admin endpoint covers all three ingestors."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from govcon_wfi.ingestors.fpds import MockFpdsAdapter, run_fpds_sync
from govcon_wfi.ingestors.sam_gov import MockSamGovAdapter, run_sam_sync
from govcon_wfi.ingestors.usaspending import (
    MockUSASpendingAdapter,
    run_usaspending_sync,
)

pytestmark = pytest.mark.asyncio


async def test_sync_status_clean_when_unrun(client):
    r = client.get("/v1/admin/sync-status")
    assert r.status_code == 200
    body = r.json()
    sources = {s["source"]: s for s in body["sources"]}
    assert sources.keys() == {"sam", "fpds", "usaspending"}
    for s in body["sources"]:
        assert s["last_sync"] is None
        assert s["records_ingested"] == 0
        assert s["error_count"] == 0
    # All zero healthy / 3 sources expected.
    assert body["health_score"] == 0.0
    assert body["totals"]["contracts"] == 0


async def test_sync_status_after_full_pipeline_runs(client, db):
    started = datetime.now(UTC)
    await run_sam_sync(MockSamGovAdapter(count=4), started=started, page_size=4)
    await run_fpds_sync(MockFpdsAdapter(count=3), started=started, limit=10)
    await run_usaspending_sync(MockUSASpendingAdapter(), started=started)

    r = client.get("/v1/admin/sync-status")
    body = r.json()
    sources = {s["source"]: s for s in body["sources"]}
    assert sources["sam"]["records_ingested"] >= 4
    assert sources["fpds"]["records_ingested"] >= 3
    assert sources["usaspending"]["last_sync"] is not None
    assert body["health_score"] == 1.0  # all 3 healthy
    assert body["totals"]["contracts"] >= 4


async def test_data_quality_rejects_missing_piid(db):
    """SAM ingestor must reject notices with no PIID/noticeId."""

    class _BadAdapter:
        async def fetch_page(self, *, posted_from, posted_to, offset, limit):
            return {
                "totalRecords": 1, "limit": limit, "offset": offset,
                "opportunitiesData": [{
                    "title": "missing-piid", "type": "Solicitation",
                    "naicsCode": "541512", "postedDate": "2026-05-01",
                }],
            }

    result = await run_sam_sync(
        _BadAdapter(), started=datetime.now(UTC), page_size=10,
    )
    assert result.upserted_contracts == 0
    assert result.rejected == 1


async def test_health_score_drops_on_failure(client, db):
    """Force a fatal in the FPDS ingestor and verify health drops."""

    class _BoomAdapter:
        async def fetch_entries(self, *, since, naics, limit):
            raise RuntimeError("simulated FPDS outage")

    await run_sam_sync(
        MockSamGovAdapter(count=2),
        started=datetime.now(UTC), page_size=2,
    )
    await run_fpds_sync(_BoomAdapter(), started=datetime.now(UTC), limit=5)

    body = client.get("/v1/admin/sync-status").json()
    sources = {s["source"]: s for s in body["sources"]}
    assert sources["fpds"]["consecutive_failures"] >= 1
    assert sources["fpds"]["last_sync"] is None
    assert body["health_score"] < 1.0
