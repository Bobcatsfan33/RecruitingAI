"""Per-source sync state in Redis (last sync time, offset, error count).

Each ingestor reads its state at the start of a run, increments counters,
and writes back when complete.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime

from govcon_wfi.redis_client import get_redis


@dataclass(frozen=True)
class SyncState:
    source: str
    last_sync: datetime | None = None
    last_offset: int = 0
    records_ingested: int = 0
    error_count: int = 0
    consecutive_failures: int = 0
    last_error: str | None = None
    cursor: str | None = None  # source-specific opaque cursor (e.g. lastModifiedDate)


class SyncStateStore:
    """Thin wrapper around Redis k/v for ingestor sync state."""

    @staticmethod
    def _key(source: str) -> str:
        return f"govcon:ingest:state:{source}"

    async def read(self, source: str) -> SyncState:
        raw = await get_redis().get(self._key(source))
        if not raw:
            return SyncState(source=source)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return SyncState(source=source)
        if data.get("last_sync"):
            try:
                data["last_sync"] = datetime.fromisoformat(data["last_sync"])
            except (TypeError, ValueError):
                data["last_sync"] = None
        return SyncState(
            source=data.get("source", source),
            last_sync=data.get("last_sync"),
            last_offset=int(data.get("last_offset", 0)),
            records_ingested=int(data.get("records_ingested", 0)),
            error_count=int(data.get("error_count", 0)),
            consecutive_failures=int(data.get("consecutive_failures", 0)),
            last_error=data.get("last_error"),
            cursor=data.get("cursor"),
        )

    async def write(self, state: SyncState) -> None:
        payload = asdict(state)
        if isinstance(payload.get("last_sync"), datetime):
            payload["last_sync"] = payload["last_sync"].isoformat()
        await get_redis().set(self._key(state.source), json.dumps(payload, default=str))


@dataclass
class IngestionResult:
    source: str
    fetched: int = 0
    upserted_contracts: int = 0
    upserted_agencies: int = 0
    upserted_vendors: int = 0
    recompete_events: int = 0
    rejected: int = 0
    errors: list[str] = field(default_factory=list)
