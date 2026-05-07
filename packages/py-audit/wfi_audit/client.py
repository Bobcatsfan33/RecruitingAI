"""ClickHouse audit logger.

Async-friendly wrapper around clickhouse-connect. Insert-only — readers exist
for the API service to surface "show me every decision on candidate X" UX.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterable
from typing import Any

import clickhouse_connect
import structlog
from clickhouse_connect.driver.client import Client

from wfi_schemas import AuditLogEntry

log = structlog.get_logger("wfi.audit")

_TABLE = "audit_log"
_DB = os.environ.get("CLICKHOUSE_DATABASE", "workforce_analytics")


def _row_for(entry: AuditLogEntry) -> list[Any]:
    return [
        entry.log_id,
        entry.timestamp,
        entry.action_type,
        entry.candidate_id,
        entry.requisition_id,
        entry.agent_type,
        entry.model_used,
        entry.input_summary,
        entry.decision,
        entry.reasoning,
        entry.confidence_score,
        entry.human_override,
        entry.override_by,
        entry.override_reason,
        entry.cost_usd,
        entry.latency_ms,
    ]


_COLUMNS = [
    "log_id",
    "timestamp",
    "action_type",
    "candidate_id",
    "requisition_id",
    "agent_type",
    "model_used",
    "input_summary",
    "decision",
    "reasoning",
    "confidence_score",
    "human_override",
    "override_by",
    "override_reason",
    "cost_usd",
    "latency_ms",
]


class AuditLogger:
    """Production audit logger backed by ClickHouse."""

    def __init__(self, client: Client, *, database: str = _DB, table: str = _TABLE):
        self._client = client
        self._database = database
        self._table = table

    @classmethod
    def from_env(cls) -> AuditLogger:
        url = os.environ.get("CLICKHOUSE_URL", "http://localhost:8123")
        # clickhouse-connect wants host/port not URL.
        from urllib.parse import urlparse

        parsed = urlparse(url)
        client = clickhouse_connect.get_client(
            host=parsed.hostname or "localhost",
            port=parsed.port or 8123,
            username=os.environ.get("CLICKHOUSE_USER", "default"),
            password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
            database=os.environ.get("CLICKHOUSE_DATABASE", _DB),
        )
        return cls(client)

    async def record(self, entry: AuditLogEntry) -> None:
        await asyncio.to_thread(self._record_sync, entry)

    def _record_sync(self, entry: AuditLogEntry) -> None:
        try:
            self._client.insert(
                f"{self._database}.{self._table}",
                [_row_for(entry)],
                column_names=_COLUMNS,
            )
        except Exception as exc:  # noqa: BLE001
            # Audit logging must never crash the calling agent. Log and drop.
            log.error("audit_insert_failed", error=str(exc), action=entry.action_type)

    async def record_many(self, entries: Iterable[AuditLogEntry]) -> None:
        rows = [_row_for(e) for e in entries]
        if not rows:
            return
        await asyncio.to_thread(
            self._client.insert,
            f"{self._database}.{self._table}",
            rows,
            column_names=_COLUMNS,
        )

    async def for_candidate(self, candidate_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return await asyncio.to_thread(
            self._for_candidate_sync, candidate_id, limit
        )

    def _for_candidate_sync(self, candidate_id: str, limit: int) -> list[dict[str, Any]]:
        result = self._client.query(
            f"""
            SELECT * FROM {self._database}.{self._table}
            WHERE candidate_id = %(cid)s
            ORDER BY timestamp DESC
            LIMIT %(lim)s
            """,
            parameters={"cid": candidate_id, "lim": limit},
        )
        return result.named_results()


class NullAuditLogger:
    """Drop-in for tests + dev when ClickHouse isn't reachable."""

    def __init__(self):
        self.entries: list[AuditLogEntry] = []

    async def record(self, entry: AuditLogEntry) -> None:
        self.entries.append(entry)

    async def record_many(self, entries: Iterable[AuditLogEntry]) -> None:
        self.entries.extend(entries)

    async def for_candidate(self, candidate_id: str, limit: int = 200) -> list[dict[str, Any]]:
        return [
            e.model_dump(mode="json")
            for e in self.entries
            if str(e.candidate_id) == str(candidate_id)
        ][:limit]
