"""USASpending enrichment tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from govcon_wfi.ingestors.sam_gov import MockSamGovAdapter, run_sam_sync
from govcon_wfi.ingestors.state import SyncStateStore
from govcon_wfi.ingestors.usaspending import (
    MockUSASpendingAdapter,
    run_usaspending_sync,
)

pytestmark = pytest.mark.asyncio


async def test_mock_returns_quarterly_obligations():
    adapter = MockUSASpendingAdapter()
    out = await adapter.fetch_award(piid="FOO-001")
    assert out is not None
    assert len(out.quarter_obligations) == 4
    assert out.trend in {"increasing", "decreasing", "flat"}


async def test_mock_returns_none_when_unavailable():
    adapter = MockUSASpendingAdapter(available_piids={"KNOWN"})
    assert await adapter.fetch_award(piid="UNKNOWN") is None


async def test_enrich_existing_contracts(db):
    # Seed contracts via the SAM ingestor first.
    await run_sam_sync(
        MockSamGovAdapter(count=5),
        started=datetime.now(UTC), page_size=5,
    )
    contracts_before = db.all_rows("contracts")
    assert contracts_before

    result = await run_usaspending_sync(
        MockUSASpendingAdapter(),
        started=datetime.now(UTC),
    )
    assert result.fetched == len(contracts_before)
    assert result.upserted_contracts == len(contracts_before)

    enriched = db.all_rows("contracts")
    for c in enriched:
        assert c.get("raw_json", {}).get("usaspending"), \
            "expected usaspending key in raw_json after enrichment"
        assert isinstance(c.get("current_value"), Decimal)


async def test_skip_unknown_piids(db):
    await run_sam_sync(
        MockSamGovAdapter(count=3),
        started=datetime.now(UTC), page_size=3,
    )
    # Mock that has no known PIIDs returns None for everything.
    adapter = MockUSASpendingAdapter(available_piids=set())
    result = await run_usaspending_sync(adapter, started=datetime.now(UTC))
    assert result.fetched == 3
    assert result.upserted_contracts == 0


async def test_state_persisted(db):
    await run_sam_sync(
        MockSamGovAdapter(count=2),
        started=datetime.now(UTC), page_size=2,
    )
    await run_usaspending_sync(
        MockUSASpendingAdapter(), started=datetime.now(UTC),
    )
    state = await SyncStateStore().read("usaspending")
    assert state.last_sync is not None
    assert state.consecutive_failures == 0
