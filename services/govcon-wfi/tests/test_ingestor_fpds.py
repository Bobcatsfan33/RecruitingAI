"""FPDS ingestor tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from govcon_wfi.ingestors.fpds import MockFpdsAdapter, run_fpds_sync
from govcon_wfi.ingestors.state import SyncStateStore

pytestmark = pytest.mark.asyncio


async def test_mock_returns_naics_filtered_entries():
    adapter = MockFpdsAdapter(count=8)
    entries = await adapter.fetch_entries(
        since=datetime(2026, 5, 1, tzinfo=UTC),
        naics=["541512", "541519"],
        limit=50,
    )
    assert len(entries) == 8
    assert all(e["naics_code"] in {"541512", "541519"} for e in entries)


async def test_run_fpds_sync_upserts_contracts(db):
    adapter = MockFpdsAdapter(count=15)
    result = await run_fpds_sync(adapter, started=datetime.now(UTC), limit=100)
    assert result.fetched == 15
    assert result.upserted_contracts == 15
    contracts = db.all_rows("contracts")
    assert {c["source"] for c in contracts} == {"fpds"}


async def test_run_fpds_sync_dedupes_against_existing(db):
    """Re-running over the same time window must not duplicate by PIID."""
    from govcon_wfi.ingestors.state import SyncState, SyncStateStore

    adapter = MockFpdsAdapter(count=10)
    started = datetime.now(UTC)
    await run_fpds_sync(adapter, started=started, limit=100)
    n_after_first = len(db.all_rows("contracts"))
    # Reset state so the second run reuses the same `since` cursor and
    # therefore generates the same fixture PIIDs.
    await SyncStateStore().write(SyncState(source="fpds"))
    await run_fpds_sync(adapter, started=started, limit=100)
    assert len(db.all_rows("contracts")) == n_after_first


async def test_run_fpds_sync_persists_state(db):
    adapter = MockFpdsAdapter(count=4)
    await run_fpds_sync(adapter, started=datetime.now(UTC), limit=100)
    state = await SyncStateStore().read("fpds")
    assert state.last_sync is not None
    assert state.records_ingested == 4
    assert state.consecutive_failures == 0


async def test_missing_pop_end_flagged_not_rejected(db):
    class _PartialAdapter:
        async def fetch_entries(self, *, since, naics, limit):
            return [{
                "piid": "FPDS-PARTIAL-001",
                "title": "Partial",
                "agency_name": "DOD",
                "agency_code": "DOD",
                "vendor_name": "Acme",
                "naics_code": "541512",
                "effective_date": "2026-01-01",
                "ultimate_completion_date": None,
                "obligated_amount": "100000",
            }]

    result = await run_fpds_sync(
        _PartialAdapter(), started=datetime.now(UTC), limit=10,
    )
    assert result.upserted_contracts == 1
    assert any("flag:missing_pop_end" in e for e in result.errors)
