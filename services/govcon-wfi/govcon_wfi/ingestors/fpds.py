"""FPDS ATOM feed ingestor.

Pulls awarded contract data from ``https://www.fpds.gov/ezsearch/FEEDNAME=PUBLIC``,
the federal procurement data system. Each feed entry is an ATOM XML document
containing a structured ``content/award`` block.

Dedupes against SAM.gov data on PIID. Incremental sync via the
``LAST_MOD_DATE`` field — we keep the most recent ``cursor`` in
``SyncState.cursor``.

Adapter pattern matches SAM: Protocol + Real (httpx + feedparser) + Mock.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

import structlog

from govcon_wfi.config import Settings
from govcon_wfi.ingestors.state import IngestionResult, SyncState, SyncStateStore
from govcon_wfi.ingestors.upsert import (
    TARGET_NAICS,
    upsert_agency,
    upsert_contract,
    upsert_vendor,
)

log = structlog.get_logger("govcon.ingest.fpds")

FPDS_FEED = "https://www.fpds.gov/ezsearch/FEEDNAME=PUBLIC"


class FpdsAdapter(Protocol):
    async def fetch_entries(
        self, *, since: datetime, naics: list[str], limit: int
    ) -> list[dict[str, Any]]: ...


class RealFpdsAdapter:
    """Real ATOM feed reader. Each entry's ``summary``/``content`` is parsed
    into a flat dict via the ``feedparser`` library."""

    async def fetch_entries(
        self, *, since: datetime, naics: list[str], limit: int
    ) -> list[dict[str, Any]]:
        import feedparser
        import httpx

        # ezsearch uses a `q=` query string. We bound by NAICS + LAST_MOD_DATE.
        naics_clause = " OR ".join(f"PRINCIPAL_NAICS_CODE:{n}" for n in naics)
        since_str = since.strftime("%Y/%m/%d")
        q = f"({naics_clause}) AND LAST_MOD_DATE:[{since_str},9999/12/31]"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(FPDS_FEED, params={"q": q, "templateName": "1.5.3"})
            resp.raise_for_status()
            parsed = feedparser.parse(resp.text)

        entries: list[dict[str, Any]] = []
        for entry in (parsed.entries or [])[:limit]:
            entries.append(_extract_atom_entry(entry))
        return entries


_PIID_RE = re.compile(r"PIID[:=]\s*([A-Z0-9-]+)", re.IGNORECASE)
_AGENCY_RE = re.compile(r"Contracting\s+Agency.*?:\s*(.+)", re.IGNORECASE)
_VENDOR_RE = re.compile(r"Vendor\s+Name.*?:\s*(.+)", re.IGNORECASE)


def _extract_atom_entry(entry: Any) -> dict[str, Any]:
    """Best-effort extraction from a FPDS ATOM entry.

    FPDS ATOM payloads embed structured fields under ``content`` as XML; the
    most robust extraction strategy in absence of a stable schema is regex
    over the entry summary plus title parsing for the PIID.
    """
    title = getattr(entry, "title", "") or ""
    summary = getattr(entry, "summary", "") or ""
    blob = f"{title}\n{summary}"
    return {
        "piid": (_PIID_RE.search(blob).group(1) if _PIID_RE.search(blob) else title.split()[0]),
        "title": title,
        "summary": summary,
        "agency_name": (_AGENCY_RE.search(summary).group(1).strip()
                        if _AGENCY_RE.search(summary) else None),
        "vendor_name": (_VENDOR_RE.search(summary).group(1).strip()
                        if _VENDOR_RE.search(summary) else None),
        "naics_code": _first_match(summary, r"NAICS[:\s]+(\d{6})"),
        "ultimate_completion_date": _first_match(
            summary, r"Ultimate Completion Date[:\s]+(\d{4}-\d{2}-\d{2})"
        ),
        "effective_date": _first_match(
            summary, r"Effective Date[:\s]+(\d{4}-\d{2}-\d{2})"
        ),
        "obligated_amount": _first_match(
            summary, r"Obligated\s+Amount[:\s]+\$?([\d,\.]+)"
        ),
        "potential_value": _first_match(
            summary, r"Total\s+Potential[^:]*[:\s]+\$?([\d,\.]+)"
        ),
        "vendor_uei": _first_match(summary, r"UEI[:\s]+([A-Z0-9]{12})"),
    }


def _first_match(text: str, pattern: str) -> str | None:
    if not text:
        return None
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


class MockFpdsAdapter:
    """Returns deterministic fake awards for tests."""

    def __init__(self, count: int = 25):
        self._count = count

    async def fetch_entries(
        self, *, since: datetime, naics: list[str], limit: int
    ) -> list[dict[str, Any]]:
        agencies = [
            ("DOD", "Department of Defense"),
            ("VA", "Department of Veterans Affairs"),
            ("DHS", "Department of Homeland Security"),
        ]
        vendors = [
            ("Booz Allen Hamilton", "ZAB1234567CD"),
            ("Leidos", "ZBC2345678DE"),
            ("ManTech", "ZCD3456789EF"),
        ]
        entries: list[dict[str, Any]] = []
        for i in range(min(self._count, limit)):
            ag_code, ag_name = agencies[i % len(agencies)]
            vname, vuei = vendors[i % len(vendors)]
            piid = f"FPDS-{since.strftime('%Y%m')}-{i:04d}"
            entries.append({
                "piid": piid,
                "title": f"{ag_name} Award {i}",
                "summary": "synthetic FPDS entry",
                "agency_name": ag_name,
                "agency_code": ag_code,
                "vendor_name": vname,
                "vendor_uei": vuei,
                "naics_code": naics[i % len(naics)],
                "effective_date": (since.date() + timedelta(days=i)).isoformat(),
                "ultimate_completion_date": (
                    since.date() + timedelta(days=365 + i)
                ).isoformat(),
                "obligated_amount": str(2_000_000 + i * 130_000),
                "potential_value": str(8_000_000 + i * 425_000),
            })
        return entries


def build_fpds_adapter(settings: Settings) -> FpdsAdapter:
    if settings.enable_real_ingestors:
        return RealFpdsAdapter()
    return MockFpdsAdapter()


def _to_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return None


def _to_decimal(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    try:
        return Decimal(raw.replace(",", ""))
    except Exception:
        return None


async def _normalize_and_upsert(
    entry: dict[str, Any], *, result: IngestionResult
) -> None:
    piid = (entry.get("piid") or "").strip()
    if not piid:
        result.rejected += 1
        result.errors.append("missing_piid")
        return

    agency_id = None
    if entry.get("agency_name") and entry.get("agency_code"):
        agency_id = await upsert_agency(
            name=entry["agency_name"], code=entry["agency_code"],
        )

    vendor_id = None
    if entry.get("vendor_name"):
        vendor_id = await upsert_vendor(
            name=entry["vendor_name"], uei=entry.get("vendor_uei"),
        )

    pop_start = _to_date(entry.get("effective_date"))
    pop_end = _to_date(entry.get("ultimate_completion_date"))
    if not pop_end:
        result.errors.append(f"flag:missing_pop_end:{piid}")

    contract_id, inserted = await upsert_contract(
        piid=piid,
        title=(entry.get("title") or "Untitled FPDS Award").strip(),
        description=entry.get("summary"),
        naics_code=entry.get("naics_code"),
        contract_vehicle=entry.get("contract_vehicle"),
        agency_id=agency_id,
        vendor_id=vendor_id,
        pop_start=pop_start,
        pop_end=pop_end,
        current_value=_to_decimal(entry.get("obligated_amount")),
        potential_value=_to_decimal(entry.get("potential_value")),
        source="fpds",
        raw_json=entry,
        is_incumbent=bool(vendor_id),
    )
    if inserted:
        result.upserted_contracts += 1
    if agency_id:
        result.upserted_agencies += 1
    if vendor_id:
        result.upserted_vendors += 1
    _ = contract_id  # contract_id reserved for future linking


async def run_fpds_sync(
    adapter: FpdsAdapter,
    *,
    started: datetime | None = None,
    limit: int = 500,
) -> IngestionResult:
    started = started or datetime.now(UTC)
    state_store = SyncStateStore()
    state = await state_store.read("fpds")
    since = state.last_sync or (started - timedelta(days=14))

    log.info("fpds_sync_started", since=since.isoformat())
    result = IngestionResult(source="fpds")
    try:
        entries = await adapter.fetch_entries(
            since=since, naics=sorted(TARGET_NAICS), limit=limit,
        )
        result.fetched = len(entries)
        for entry in entries:
            try:
                await _normalize_and_upsert(entry, result=result)
            except Exception as exc:
                result.rejected += 1
                result.errors.append(str(exc)[:200])
    except Exception as exc:
        result.errors.append(f"fatal: {exc}")
        await state_store.write(SyncState(
            source="fpds",
            last_sync=state.last_sync,
            records_ingested=state.records_ingested + result.upserted_contracts,
            error_count=state.error_count + 1,
            consecutive_failures=state.consecutive_failures + 1,
            last_error=str(exc)[:500],
        ))
        log.error("fpds_sync_failed", error=str(exc))
        return result

    await state_store.write(SyncState(
        source="fpds",
        last_sync=datetime.now(UTC),
        records_ingested=state.records_ingested + result.upserted_contracts,
        error_count=state.error_count,
        consecutive_failures=0,
        last_error=None,
    ))
    log.info(
        "fpds_sync_complete",
        fetched=result.fetched, upserted=result.upserted_contracts,
        rejected=result.rejected,
    )
    return result
