"""Shared upsert helpers used by every ingestor.

Each helper handles deduplication keys and ensures the in-memory + asyncpg
implementations stay in sync.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from govcon_wfi.db import get_database
from govcon_wfi.embeddings import get_embedder

# NAICS codes for IT / professional services per the build spec.
TARGET_NAICS = {
    "541511",
    "541512",
    "541513",
    "541519",
    "541611",
    "541690",
    "561320",
}


async def upsert_agency(
    *, name: str, code: str, department: str | None = None
) -> UUID:
    db = get_database()
    if not name or not code:
        raise ValueError("agency name and code are required")
    existing = await db.list_rows("agencies", filters={"code": code}, limit=1)
    if existing:
        return existing[0]["id"]
    row = await db.insert_returning(
        "agencies",
        ["id", "name", "code", "department"],
        [uuid4(), name, code, department],
    )
    return row["id"]


async def upsert_vendor(
    *, name: str, uei: str | None = None, set_aside_type: str | None = None,
    size_standard: str | None = None,
) -> UUID | None:
    if not name:
        return None
    db = get_database()
    if uei:
        existing = await db.list_rows("vendors", filters={"uei": uei}, limit=1)
        if existing:
            return existing[0]["id"]
    row = await db.insert_returning(
        "vendors",
        ["id", "name", "uei", "size_standard", "set_aside_type"],
        [uuid4(), name, uei, size_standard, set_aside_type or "none"],
    )
    return row["id"]


async def upsert_contract(
    *,
    piid: str,
    title: str,
    description: str | None,
    naics_code: str | None,
    contract_vehicle: str | None,
    agency_id: UUID | None,
    vendor_id: UUID | None,
    pop_start: date | None,
    pop_end: date | None,
    current_value: Decimal | None,
    potential_value: Decimal | None,
    source: str,
    raw_json: dict[str, Any] | None,
    is_incumbent: bool = False,
) -> tuple[UUID, bool]:
    """Upsert by PIID. Returns ``(contract_id, was_inserted)``."""
    db = get_database()
    existing = await db.list_rows("contracts", filters={"piid": piid}, limit=1)
    embedding = await get_embedder().embed(
        " ".join(filter(None, [title, description, naics_code]))
    )
    now = datetime.now(UTC)
    if existing:
        cid = existing[0]["id"]
        cols = [
            "title", "description", "naics_code", "contract_vehicle",
            "agency_id", "vendor_id", "pop_start", "pop_end",
            "current_value", "potential_value", "source", "raw_json",
            "is_incumbent", "embedding", "last_synced_at",
        ]
        vals = [
            title, description, naics_code, contract_vehicle,
            agency_id, vendor_id, pop_start, pop_end,
            current_value, potential_value, source, raw_json,
            is_incumbent, embedding, now,
        ]
        await db.update_returning("contracts", "id", cid, cols, vals)
        return cid, False

    row = await db.insert_returning(
        "contracts",
        [
            "id", "piid", "title", "description", "naics_code",
            "contract_vehicle", "agency_id", "vendor_id", "pop_start",
            "pop_end", "current_value", "potential_value", "option_year",
            "base_or_option", "is_incumbent", "status", "source",
            "raw_json", "embedding", "last_synced_at",
        ],
        [
            uuid4(), piid, title, description, naics_code,
            contract_vehicle, agency_id, vendor_id, pop_start,
            pop_end, current_value, potential_value, 0,
            "base", is_incumbent, "active", source,
            raw_json, embedding, now,
        ],
    )
    return row["id"], True


async def upsert_recompete_event(
    *,
    contract_id: UUID,
    event_type: str,
    detected_date: date,
    sam_notice_id: str | None = None,
    response_deadline: date | None = None,
    details: dict[str, Any] | None = None,
) -> UUID:
    """Insert a recompete event, deduplicated on sam_notice_id when present."""
    db = get_database()
    if sam_notice_id:
        existing = await db.list_rows(
            "recompete_events", filters={"sam_notice_id": sam_notice_id}, limit=1
        )
        if existing:
            return existing[0]["id"]
    row = await db.insert_returning(
        "recompete_events",
        [
            "id", "contract_id", "event_type", "detected_date",
            "sam_notice_id", "response_deadline", "details",
        ],
        [
            uuid4(), contract_id, event_type, detected_date,
            sam_notice_id, response_deadline, details,
        ],
    )
    return row["id"]
