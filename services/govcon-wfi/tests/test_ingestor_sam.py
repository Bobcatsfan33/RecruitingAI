"""SAM.gov ingestor tests using the mock adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from govcon_wfi.ingestors.sam_gov import MockSamGovAdapter, run_sam_sync
from govcon_wfi.ingestors.state import SyncStateStore

pytestmark = pytest.mark.asyncio


async def test_mock_adapter_returns_paged_response():
    adapter = MockSamGovAdapter(count=12)
    page = await adapter.fetch_page(
        posted_from=datetime(2026, 5, 1).date(),
        posted_to=datetime(2026, 5, 13).date(),
        offset=0, limit=5,
    )
    assert page["totalRecords"] == 12
    assert len(page["opportunitiesData"]) == 5
    assert all("naicsCode" in n for n in page["opportunitiesData"])


async def test_run_sam_sync_upserts_contracts(db):
    adapter = MockSamGovAdapter(count=10)
    started = datetime.now(UTC)
    result = await run_sam_sync(adapter, started=started, page_size=10)

    assert result.fetched == 10
    assert result.upserted_contracts == 10
    assert result.recompete_events == 10
    assert result.rejected == 0
    assert db.all_rows("contracts")
    assert db.all_rows("agencies")
    assert db.all_rows("recompete_events")


async def test_run_sam_sync_is_idempotent(db):
    adapter = MockSamGovAdapter(count=8)
    started = datetime.now(UTC)
    await run_sam_sync(adapter, started=started, page_size=8)
    contracts_after_first = len(db.all_rows("contracts"))
    # Second run on the same fixture should not duplicate by PIID.
    await run_sam_sync(adapter, started=started, page_size=8)
    assert len(db.all_rows("contracts")) == contracts_after_first


async def test_run_sam_sync_persists_sync_state(db):
    adapter = MockSamGovAdapter(count=5)
    await run_sam_sync(adapter, started=datetime.now(UTC), page_size=5)
    state = await SyncStateStore().read("sam")
    assert state.last_sync is not None
    assert state.records_ingested == 5
    assert state.consecutive_failures == 0


async def test_award_notice_records_vendor(db):
    adapter = MockSamGovAdapter(count=3)
    await run_sam_sync(adapter, started=datetime.now(UTC), page_size=3)
    # The fixture cycles through notice types 0,1,2 → index 2 is Award Notice.
    vendors = db.all_rows("vendors")
    assert vendors, "expected at least one vendor from award notice"
    assert any(v.get("name") == "Acme Federal Solutions" for v in vendors)


async def test_pagination_loops_until_total_reached(db):
    adapter = MockSamGovAdapter(count=23)
    result = await run_sam_sync(
        adapter, started=datetime.now(UTC), page_size=10,
    )
    assert result.fetched == 23
    assert result.upserted_contracts == 23
