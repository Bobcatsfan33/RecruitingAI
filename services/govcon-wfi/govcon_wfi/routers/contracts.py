"""Contracts CRUD + listing + semantic search.

Search params (GET /v1/contracts):
- ``agency`` — agency name or code substring (case-insensitive)
- ``vendor`` — vendor name or UEI substring
- ``naics`` — exact NAICS code match
- ``pop_end_before`` / ``pop_end_after`` — date filters
- ``q`` — substring match on title + description
- ``semantic_q`` — embedding cosine search via pgvector (or in-memory fallback)
- ``status`` — active / expired / cancelled
- ``risk`` — CRITICAL / HIGH / WATCH / STABLE
- ``sort`` — pop_end / value / risk / created_at (default: created_at)
- ``page`` / ``page_size`` — 1-indexed pagination, page_size 1..200, default 50
"""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from wfi_schemas import (
    Agency,
    Assignment,
    Contract,
    ContractCreate,
    ContractUpdate,
    GapAnalysis,
    Lcat,
    RecompeteEvent,
    Vendor,
)

from govcon_wfi.db import get_database
from govcon_wfi.deps import AuditEvent, get_audit
from govcon_wfi.embeddings import get_embedder

router = APIRouter(prefix="/v1/contracts", tags=["contracts"])
log = structlog.get_logger("govcon.contracts")


_RISK_RANK = {"CRITICAL": 0, "HIGH": 1, "WATCH": 2, "STABLE": 3, None: 4}
_VALID_SORT = {"pop_end", "value", "risk", "created_at"}


class ContractListResponse(BaseModel):
    items: list[Contract]
    total: int
    page: int
    page_size: int


class ContractDetail(BaseModel):
    contract: Contract
    agency: Agency | None = None
    vendor: Vendor | None = None
    lcats: list[Lcat] = []
    recompete_events: list[RecompeteEvent] = []
    assignments: list[Assignment] = []
    gap_analyses: list[GapAnalysis] = []


def _to_contract(row: dict[str, Any]) -> Contract:
    payload = {k: v for k, v in row.items() if k != "embedding"}
    return Contract.model_validate(payload)


def _embedding_text(c: ContractCreate | Contract) -> str:
    bits = [c.title or ""]
    if c.description:
        bits.append(c.description)
    if c.naics_code:
        bits.append(f"NAICS {c.naics_code}")
    return " ".join(bits)


async def _embed_for(c: ContractCreate | Contract) -> list[float]:
    return await get_embedder().embed(_embedding_text(c))


@router.post("", response_model=Contract, status_code=201)
async def create_contract(body: ContractCreate) -> Contract:
    db = get_database()
    audit = get_audit()
    # Reject duplicates on PIID — that's the federal unique key.
    existing = await db.list_rows("contracts", filters={"piid": body.piid}, limit=1)
    if existing:
        raise HTTPException(409, f"contract with piid {body.piid} already exists")
    embedding = await _embed_for(body)
    payload = body.model_dump(mode="python")
    payload["embedding"] = embedding
    inserted = await db.insert_returning(
        "contracts",
        list(payload.keys()),
        list(payload.values()),
    )
    contract = _to_contract(inserted)
    await audit.record(
        AuditEvent(
            actor="api",
            action="contract.create",
            resource_type="contract",
            resource_id=str(contract.id),
            detail={"piid": contract.piid, "source": str(contract.source)},
        )
    )
    return contract


@router.get("/{contract_id}", response_model=ContractDetail)
async def get_contract(contract_id: UUID) -> ContractDetail:
    db = get_database()
    row = await db.get_row("contracts", "id", contract_id)
    if row is None:
        raise HTTPException(404, "contract not found")
    contract = _to_contract(row)

    agency = None
    if row.get("agency_id"):
        ar = await db.get_row("agencies", "id", row["agency_id"])
        agency = Agency.model_validate(ar) if ar else None

    vendor = None
    if row.get("vendor_id"):
        vr = await db.get_row("vendors", "id", row["vendor_id"])
        vendor = Vendor.model_validate(vr) if vr else None

    lcats = [
        Lcat.model_validate(r)
        for r in await db.list_rows("lcats", filters={"contract_id": contract_id}, limit=200)
    ]
    recompete_events = [
        RecompeteEvent.model_validate(r)
        for r in await db.list_rows(
            "recompete_events", filters={"contract_id": contract_id}, limit=200,
        )
    ]
    assignments = [
        Assignment.model_validate(r)
        for r in await db.list_rows(
            "assignments", filters={"contract_id": contract_id}, limit=200,
        )
    ]
    gap_analyses = [
        GapAnalysis.model_validate(r)
        for r in await db.list_rows(
            "gap_analyses", filters={"contract_id": contract_id}, limit=200,
        )
    ]
    return ContractDetail(
        contract=contract,
        agency=agency,
        vendor=vendor,
        lcats=lcats,
        recompete_events=recompete_events,
        assignments=assignments,
        gap_analyses=gap_analyses,
    )


@router.patch("/{contract_id}", response_model=Contract)
async def update_contract(contract_id: UUID, body: ContractUpdate) -> Contract:
    db = get_database()
    audit = get_audit()
    diff = body.model_dump(exclude_unset=True, mode="python")
    if not diff:
        existing = await db.get_row("contracts", "id", contract_id)
        if existing is None:
            raise HTTPException(404, "contract not found")
        return _to_contract(existing)
    updated = await db.update_returning(
        "contracts", "id", contract_id, list(diff.keys()), list(diff.values())
    )
    if updated is None:
        raise HTTPException(404, "contract not found")
    await audit.record(
        AuditEvent(
            actor="api",
            action="contract.update",
            resource_type="contract",
            resource_id=str(contract_id),
            detail={"fields": list(diff.keys())},
        )
    )
    return _to_contract(updated)


def _matches(row: dict[str, Any], **filters: Any) -> bool:
    for key, val in filters.items():
        if val is None:
            continue
        if key in {"agency", "vendor"}:
            continue  # handled separately (need joins / substring)
        if key == "naics":
            if (row.get("naics_code") or "") != val:
                return False
        elif key == "pop_end_before":
            pop = row.get("pop_end")
            if not pop or pop > val:
                return False
        elif key == "pop_end_after":
            pop = row.get("pop_end")
            if not pop or pop < val:
                return False
        elif key == "status":
            if str(row.get("status")) != val:
                return False
        elif key == "risk":
            if str(row.get("recompete_risk") or "") != val:
                return False
        elif key == "q":
            hay = f"{row.get('title') or ''} {row.get('description') or ''}".lower()
            if val.lower() not in hay:
                return False
    return True


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _sort_key(row: dict[str, Any], by: str) -> Any:
    if by == "pop_end":
        return row.get("pop_end") or date.min
    if by == "value":
        return row.get("current_value") or Decimal("0")
    if by == "risk":
        return _RISK_RANK.get(str(row.get("recompete_risk") or ""), 5)
    return row.get("created_at")


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    agency: str | None = Query(default=None),
    vendor: str | None = Query(default=None),
    naics: str | None = Query(default=None),
    pop_end_before: date | None = Query(default=None),
    pop_end_after: date | None = Query(default=None),
    q: str | None = Query(default=None),
    semantic_q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    risk: str | None = Query(default=None),
    sort: str = Query(default="created_at"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> ContractListResponse:
    if sort not in _VALID_SORT:
        raise HTTPException(400, f"sort must be one of {sorted(_VALID_SORT)}")
    db = get_database()
    rows = await db.list_rows("contracts", limit=10_000, offset=0)

    if agency:
        agencies = await db.list_rows("agencies", limit=10_000, offset=0)
        ag_lower = agency.lower()
        ids = {
            a["id"]
            for a in agencies
            if ag_lower in (a.get("name") or "").lower()
            or ag_lower in (a.get("code") or "").lower()
        }
        rows = [r for r in rows if r.get("agency_id") in ids]

    if vendor:
        vendors = await db.list_rows("vendors", limit=10_000, offset=0)
        v_lower = vendor.lower()
        ids = {
            v["id"]
            for v in vendors
            if v_lower in (v.get("name") or "").lower()
            or v_lower in (v.get("uei") or "").lower()
        }
        rows = [r for r in rows if r.get("vendor_id") in ids]

    rows = [
        r for r in rows
        if _matches(
            r,
            naics=naics,
            pop_end_before=pop_end_before,
            pop_end_after=pop_end_after,
            status=status,
            risk=risk,
            q=q,
        )
    ]

    if semantic_q:
        query_vec = await get_embedder().embed(semantic_q)
        rows.sort(
            key=lambda r: _cosine(r.get("embedding") or [], query_vec),
            reverse=True,
        )
    else:
        rows.sort(key=lambda r: _sort_key(r, sort), reverse=True)

    total = len(rows)
    start = (page - 1) * page_size
    sliced = rows[start : start + page_size]
    return ContractListResponse(
        items=[_to_contract(r) for r in sliced],
        total=total,
        page=page,
        page_size=page_size,
    )
