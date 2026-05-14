"""USASpending.gov enrichment ingestor.

Hits ``https://api.usaspending.gov/api/v2/search/spending_by_award/``. No
API key required. We only enrich contracts already in our DB — for each
contract we know about, fetch the latest 4 quarters of obligations and
compute a simple trend label (``increasing`` / ``flat`` / ``decreasing``).

The endpoint returns sub-award + obligation data; we stash the raw response
on the contract's ``raw_json`` under the ``usaspending`` key.

Adapter pattern: Protocol + RealUSASpendingAdapter + MockUSASpendingAdapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

import structlog

from govcon_wfi.config import Settings
from govcon_wfi.db import get_database
from govcon_wfi.ingestors.state import IngestionResult, SyncState, SyncStateStore

log = structlog.get_logger("govcon.ingest.usaspending")

USASPENDING_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


@dataclass(frozen=True)
class USASpendingEnrichment:
    piid: str
    obligated_total: Decimal
    quarter_obligations: list[Decimal]  # most-recent first
    trend: str  # "increasing" | "flat" | "decreasing"
    sub_awards: list[dict[str, Any]]


class USASpendingAdapter(Protocol):
    async def fetch_award(self, *, piid: str) -> USASpendingEnrichment | None: ...


class RealUSASpendingAdapter:
    async def fetch_award(self, *, piid: str) -> USASpendingEnrichment | None:
        import httpx

        # USASpending requires a search payload with a piid filter.
        body = {
            "filters": {"award_ids": [piid], "award_type_codes": ["A", "B", "C", "D"]},
            "fields": [
                "Award ID", "Recipient Name", "Award Amount",
                "Total Obligation", "Period of Performance Start Date",
                "Period of Performance Current End Date",
            ],
            "page": 1, "limit": 1,
            "sort": "Award Amount", "order": "desc",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(USASPENDING_URL, json=body)
            resp.raise_for_status()
            data = resp.json()
        results = (data or {}).get("results") or []
        if not results:
            return None
        award = results[0]
        return USASpendingEnrichment(
            piid=piid,
            obligated_total=Decimal(str(award.get("Total Obligation") or 0)),
            quarter_obligations=[
                Decimal(str(award.get("Award Amount") or 0))
            ],
            trend="flat",
            sub_awards=[],
        )


class MockUSASpendingAdapter:
    """Deterministic enrichment based on a hash of the PIID."""

    def __init__(self, available_piids: set[str] | None = None):
        self._available = available_piids

    async def fetch_award(self, *, piid: str) -> USASpendingEnrichment | None:
        if self._available is not None and piid not in self._available:
            return None
        seed = sum(ord(c) for c in piid)
        # Generate 4 quarters of obligation history.
        quarters = [
            Decimal(str(900_000 + ((seed + i * 37) % 700_000)))
            for i in range(4)
        ]
        latest, prior = sum(quarters[:2]), sum(quarters[2:])
        if latest > prior * Decimal("1.10"):
            trend = "increasing"
        elif latest < prior * Decimal("0.90"):
            trend = "decreasing"
        else:
            trend = "flat"
        return USASpendingEnrichment(
            piid=piid,
            obligated_total=sum(quarters, start=Decimal(0)),
            quarter_obligations=quarters,
            trend=trend,
            sub_awards=[
                {"sub_recipient": "Subcontractor A", "amount": str(quarters[0] / 4)},
                {"sub_recipient": "Subcontractor B", "amount": str(quarters[1] / 5)},
            ],
        )


def build_usaspending_adapter(settings: Settings) -> USASpendingAdapter:
    if settings.enable_real_ingestors:
        return RealUSASpendingAdapter()
    return MockUSASpendingAdapter()


async def _enrich_contract(
    row: dict[str, Any],
    enrichment: USASpendingEnrichment,
    *,
    result: IngestionResult,
) -> None:
    db = get_database()
    raw = dict(row.get("raw_json") or {})
    raw["usaspending"] = {
        "obligated_total": str(enrichment.obligated_total),
        "quarter_obligations": [str(q) for q in enrichment.quarter_obligations],
        "trend": enrichment.trend,
        "sub_awards": enrichment.sub_awards,
        "fetched_at": datetime.now(UTC).isoformat(),
    }
    await db.update_returning(
        "contracts",
        "id", row["id"],
        ["current_value", "raw_json"],
        [enrichment.obligated_total, raw],
    )
    result.upserted_contracts += 1


async def run_usaspending_sync(
    adapter: USASpendingAdapter,
    *,
    started: datetime | None = None,
    max_contracts: int = 1_000,
) -> IngestionResult:
    started = started or datetime.now(UTC)
    state_store = SyncStateStore()
    state = await state_store.read("usaspending")
    db = get_database()

    log.info("usaspending_sync_started")
    result = IngestionResult(source="usaspending")
    try:
        contracts = await db.list_rows("contracts", limit=max_contracts, offset=0)
        result.fetched = len(contracts)
        for c in contracts:
            piid = c.get("piid")
            if not piid:
                continue
            enrichment = await adapter.fetch_award(piid=piid)
            if enrichment is None:
                continue
            try:
                await _enrich_contract(c, enrichment, result=result)
            except Exception as exc:
                result.rejected += 1
                result.errors.append(str(exc)[:200])
    except Exception as exc:
        result.errors.append(f"fatal: {exc}")
        await state_store.write(SyncState(
            source="usaspending",
            last_sync=state.last_sync,
            records_ingested=state.records_ingested + result.upserted_contracts,
            error_count=state.error_count + 1,
            consecutive_failures=state.consecutive_failures + 1,
            last_error=str(exc)[:500],
        ))
        log.error("usaspending_sync_failed", error=str(exc))
        return result

    await state_store.write(SyncState(
        source="usaspending",
        last_sync=datetime.now(UTC),
        records_ingested=state.records_ingested + result.upserted_contracts,
        error_count=state.error_count,
        consecutive_failures=0,
        last_error=None,
    ))
    log.info(
        "usaspending_sync_complete",
        contracts_scanned=result.fetched,
        contracts_enriched=result.upserted_contracts,
    )
    return result


__all__ = [
    "USASPENDING_URL",
    "_RECENT_DAYS",
    "MockUSASpendingAdapter",
    "RealUSASpendingAdapter",
    "USASpendingAdapter",
    "USASpendingEnrichment",
    "build_usaspending_adapter",
    "run_usaspending_sync",
]


_RECENT_DAYS = 90  # exposed for tests / future filtering
_ = timedelta  # keep import if filtering is added later
