"""Admin router — sync status (Sprint 2.4 fills this out)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from govcon_wfi.db import get_database
from govcon_wfi.ingestors.state import SyncStateStore

router = APIRouter(prefix="/v1/admin", tags=["admin"])


class SyncStatus(BaseModel):
    source: str
    last_sync: datetime | None
    records_ingested: int
    error_count: int
    consecutive_failures: int


class SyncStatusResponse(BaseModel):
    sources: list[SyncStatus]
    totals: dict[str, int]
    health_score: float
    generated_at: datetime


@router.get("/sync-status", response_model=SyncStatusResponse)
async def sync_status() -> SyncStatusResponse:
    db = get_database()
    state = SyncStateStore()
    sources = []
    healthy = 0
    for src in ("sam", "fpds", "usaspending"):
        s = await state.read(src)
        sources.append(
            SyncStatus(
                source=src,
                last_sync=s.last_sync,
                records_ingested=s.records_ingested,
                error_count=s.error_count,
                consecutive_failures=s.consecutive_failures,
            )
        )
        if s.last_sync and s.consecutive_failures == 0:
            healthy += 1

    totals = await _totals(db)
    health = healthy / 3.0
    return SyncStatusResponse(
        sources=sources,
        totals=totals,
        health_score=round(health, 2),
        generated_at=datetime.now(timezone.utc),
    )


async def _totals(db: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for table in ("contracts", "agencies", "vendors", "employees"):
        rows = await db.list_rows(table, limit=100_000, offset=0)
        out[table] = len(rows)
    return out
