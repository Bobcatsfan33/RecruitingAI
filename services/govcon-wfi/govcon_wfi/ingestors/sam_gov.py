"""SAM.gov Opportunities ingestor.

Hits ``https://api.sam.gov/opportunities/v2/search``. Filters by NAICS codes
in ``TARGET_NAICS`` and notice types ``o`` (solicitation), ``r`` (sources
sought), ``a`` (award notice). Pages with ``limit`` + ``offset``. Honours a
10 req/sec rate limit.

Adapter pattern:
- ``SamGovAdapter`` — Protocol
- ``RealSamGovAdapter`` — live HTTP client
- ``MockSamGovAdapter`` — returns 50 deterministic fake notices for tests
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
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
    upsert_recompete_event,
    upsert_vendor,
)

log = structlog.get_logger("govcon.ingest.sam")

SAM_API_URL = "https://api.sam.gov/opportunities/v2/search"
NOTICE_TYPES = ("o", "r", "a")  # solicitation, sources sought, award


class SamGovAdapter(Protocol):
    async def fetch_page(self, *, posted_from: date, posted_to: date,
                         offset: int, limit: int) -> dict[str, Any]: ...


class _RateLimiter:
    """Token-bucket-ish limiter (10 req/sec by default)."""

    def __init__(self, per_second: float = 10.0):
        self._interval = 1.0 / per_second
        self._next: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now < self._next:
                await asyncio.sleep(self._next - now)
            self._next = max(self._next, time.monotonic()) + self._interval


class RealSamGovAdapter:
    def __init__(self, api_key: str, *, rate: float = 10.0):
        self._api_key = api_key
        self._limiter = _RateLimiter(rate)

    async def fetch_page(
        self, *, posted_from: date, posted_to: date, offset: int, limit: int
    ) -> dict[str, Any]:
        import httpx

        await self._limiter.acquire()
        params = {
            "api_key": self._api_key,
            "postedFrom": posted_from.strftime("%m/%d/%Y"),
            "postedTo": posted_to.strftime("%m/%d/%Y"),
            "limit": limit,
            "offset": offset,
            "ncode": ",".join(sorted(TARGET_NAICS)),
            "ptype": ",".join(NOTICE_TYPES),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(SAM_API_URL, params=params)
            resp.raise_for_status()
            return resp.json()


class MockSamGovAdapter:
    """Deterministic fake adapter — returns 50 NAICS-filtered notices."""

    def __init__(self, count: int = 50):
        self._count = count

    async def fetch_page(
        self, *, posted_from: date, posted_to: date, offset: int, limit: int
    ) -> dict[str, Any]:
        all_notices = list(self._fixture(posted_from))
        page = all_notices[offset : offset + limit]
        return {
            "totalRecords": len(all_notices),
            "limit": limit,
            "offset": offset,
            "opportunitiesData": page,
        }

    def _fixture(self, posted_from: date) -> Iterator[dict[str, Any]]:
        agencies = [
            ("DOD", "Department of Defense"),
            ("VA", "Department of Veterans Affairs"),
            ("DHS", "Department of Homeland Security"),
            ("HHS", "Department of Health and Human Services"),
            ("GSA", "General Services Administration"),
        ]
        naics = sorted(TARGET_NAICS)
        notice_types = ["Solicitation", "Sources Sought", "Award Notice"]
        for i in range(self._count):
            ag_code, ag_name = agencies[i % len(agencies)]
            piid = f"MOCK-SAM-{posted_from.strftime('%Y%m')}-{i:04d}"
            yield {
                "noticeId": f"notice-{piid}",
                "title": f"{ag_name} IT Services Task Order #{i}",
                "solicitationNumber": piid,
                "fullParentPathName": ag_name,
                "fullParentPathCode": ag_code,
                "postedDate": (posted_from + timedelta(days=i % 14)).isoformat(),
                "type": notice_types[i % 3],
                "baseType": notice_types[i % 3],
                "naicsCode": naics[i % len(naics)],
                "classificationCode": naics[i % len(naics)],
                "responseDeadLine": (posted_from + timedelta(days=30 + i)).isoformat(),
                "description": (
                    f"Mock SAM.gov fixture for {ag_name}. "
                    "Cloud, DevSecOps, and platform engineering services."
                ),
                "setAside": ["", "8a", "SDVOSB", "HUBZONE", "WOSB"][i % 5],
                "placeOfPerformance": {
                    "city": {"name": "Arlington"}, "state": {"code": "VA"},
                },
                "pointOfContact": [
                    {"fullName": "Jane Doe", "email": f"contact-{i}@gov"}
                ],
                "awardee": (
                    {"name": "Acme Federal Solutions", "ueiSAM": f"MOCKUEI{i:09d}"[:12]}
                    if notice_types[i % 3] == "Award Notice" else None
                ),
                "award": (
                    {"amount": str(1_000_000 + (i * 137_000))}
                    if notice_types[i % 3] == "Award Notice" else None
                ),
            }


def build_sam_adapter(settings: Settings) -> SamGovAdapter:
    if settings.enable_real_ingestors and settings.sam_gov_api_key:
        return RealSamGovAdapter(settings.sam_gov_api_key)
    return MockSamGovAdapter()


_NOTICE_TO_EVENT = {
    "Solicitation": "solicitation",
    "Sources Sought": "sources_sought",
    "Award Notice": "award",
    "Special Notice": "solicitation",
    "Combined Synopsis/Solicitation": "solicitation",
    "Justification": "solicitation",
}


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    # Accepts "YYYY-MM-DD" or full ISO with TZ.
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(raw[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _normalize_set_aside(raw: str | None) -> str:
    if not raw:
        return "none"
    val = raw.strip().upper()
    mapping = {"8A": "8a", "SDVOSB": "SDVOSB", "HUBZONE": "HUBZONE", "WOSB": "WOSB"}
    return mapping.get(val, "none")


async def _normalize_and_upsert(
    notice: dict[str, Any], *, result: IngestionResult
) -> None:
    piid = notice.get("solicitationNumber") or notice.get("noticeId")
    if not piid:
        result.rejected += 1
        result.errors.append("missing_piid")
        return

    title = (notice.get("title") or "Untitled").strip()
    description = (notice.get("description") or "")[:5000]
    naics = notice.get("naicsCode") or notice.get("classificationCode")
    notice_type = notice.get("type") or notice.get("baseType") or ""
    posted = _parse_date(notice.get("postedDate"))
    response_deadline = _parse_date(notice.get("responseDeadLine"))

    agency_id = None
    code = notice.get("fullParentPathCode")
    name = notice.get("fullParentPathName")
    if code and name:
        agency_id = await upsert_agency(name=name, code=code)

    vendor_id = None
    awardee = notice.get("awardee") or {}
    if isinstance(awardee, dict) and awardee.get("name"):
        vendor_id = await upsert_vendor(
            name=awardee.get("name"),
            uei=awardee.get("ueiSAM") or awardee.get("uei"),
            set_aside_type=_normalize_set_aside(notice.get("setAside")),
        )

    award = notice.get("award") or {}
    current_value = None
    if isinstance(award, dict) and award.get("amount"):
        try:
            current_value = Decimal(str(award["amount"]))
        except Exception:
            current_value = None

    contract_id, inserted = await upsert_contract(
        piid=str(piid),
        title=title,
        description=description,
        naics_code=naics,
        contract_vehicle=notice.get("contractVehicle"),
        agency_id=agency_id,
        vendor_id=vendor_id,
        pop_start=None,
        pop_end=response_deadline,
        current_value=current_value,
        potential_value=None,
        source="sam",
        raw_json=notice,
        is_incumbent=bool(awardee),
    )
    if inserted:
        result.upserted_contracts += 1
    if agency_id:
        result.upserted_agencies += 1
    if vendor_id:
        result.upserted_vendors += 1

    event_type = _NOTICE_TO_EVENT.get(notice_type, "solicitation")
    if posted:
        await upsert_recompete_event(
            contract_id=contract_id,
            event_type=event_type,
            detected_date=posted,
            sam_notice_id=notice.get("noticeId"),
            response_deadline=response_deadline,
            details={"raw_type": notice_type, "set_aside": notice.get("setAside")},
        )
        result.recompete_events += 1


async def run_sam_sync(
    adapter: SamGovAdapter,
    *,
    started: datetime | None = None,
    page_size: int = 100,
    max_pages: int = 20,
) -> IngestionResult:
    started = started or datetime.now(UTC)
    state_store = SyncStateStore()
    state = await state_store.read("sam")
    posted_from = (
        state.last_sync.date() if state.last_sync else (started - timedelta(days=7)).date()
    )
    posted_to = started.date()
    log.info("sam_sync_started", posted_from=str(posted_from), posted_to=str(posted_to))

    result = IngestionResult(source="sam")
    offset = 0
    pages = 0
    try:
        while pages < max_pages:
            page = await adapter.fetch_page(
                posted_from=posted_from, posted_to=posted_to,
                offset=offset, limit=page_size,
            )
            notices = page.get("opportunitiesData", []) or []
            result.fetched += len(notices)
            for notice in notices:
                try:
                    await _normalize_and_upsert(notice, result=result)
                except Exception as exc:
                    result.rejected += 1
                    result.errors.append(str(exc)[:200])
            total = int(page.get("totalRecords", 0) or 0)
            offset += len(notices)
            pages += 1
            if not notices or offset >= total:
                break
    except Exception as exc:
        result.errors.append(f"fatal: {exc}")
        await state_store.write(SyncState(
            source="sam",
            last_sync=state.last_sync,
            last_offset=offset,
            records_ingested=state.records_ingested + result.upserted_contracts,
            error_count=state.error_count + 1,
            consecutive_failures=state.consecutive_failures + 1,
            last_error=str(exc)[:500],
            cursor=str(posted_to),
        ))
        log.error("sam_sync_failed", error=str(exc))
        return result

    await state_store.write(SyncState(
        source="sam",
        last_sync=datetime.now(UTC),
        last_offset=0,
        records_ingested=state.records_ingested + result.upserted_contracts,
        error_count=state.error_count,
        consecutive_failures=0,
        last_error=None,
        cursor=str(posted_to),
    ))
    log.info(
        "sam_sync_complete",
        fetched=result.fetched, upserted=result.upserted_contracts,
        events=result.recompete_events, rejected=result.rejected,
    )
    return result
