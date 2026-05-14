"""Audit-log adapter for the GovCon service.

Reuses the ClickHouse connection pattern from ``packages/py-audit`` but writes
to a dedicated ``govcon_audit_log`` table because the Pydantic shape for the
existing recruiting AuditLogEntry (candidate-centric) doesn't fit
contract/employee/recompete events.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any, Protocol
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, ConfigDict, Field

log = structlog.get_logger("govcon.audit")

_TABLE = "govcon_audit_log"
_DB = os.environ.get("CLICKHOUSE_DATABASE", "workforce_analytics")


class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = "system"
    action: str
    resource_type: str
    resource_id: str
    detail: dict[str, Any] = Field(default_factory=dict)


class AuditWriter(Protocol):
    async def record(self, event: AuditEvent) -> None: ...
    async def record_many(self, events: Iterable[AuditEvent]) -> None: ...


class ClickHouseAuditWriter:
    """Production audit writer backed by ClickHouse."""

    _COLUMNS = [
        "log_id",
        "timestamp",
        "actor",
        "action",
        "resource_type",
        "resource_id",
        "detail_json",
    ]

    def __init__(self, client: Any, *, database: str = _DB, table: str = _TABLE):
        self._client = client
        self._database = database
        self._table = table

    @classmethod
    def from_env(cls) -> "ClickHouseAuditWriter":
        import clickhouse_connect  # noqa: PLC0415
        from urllib.parse import urlparse  # noqa: PLC0415

        parsed = urlparse(os.environ.get("CLICKHOUSE_URL", "http://localhost:8123"))
        client = clickhouse_connect.get_client(
            host=parsed.hostname or "localhost",
            port=parsed.port or 8123,
            username=os.environ.get("CLICKHOUSE_USER", "default"),
            password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
            database=os.environ.get("CLICKHOUSE_DATABASE", _DB),
        )
        return cls(client)

    async def record(self, event: AuditEvent) -> None:
        await asyncio.to_thread(self._record_sync, event)

    def _record_sync(self, event: AuditEvent) -> None:
        import json  # noqa: PLC0415

        try:
            self._client.insert(
                f"{self._database}.{self._table}",
                [
                    [
                        event.log_id,
                        event.timestamp,
                        event.actor,
                        event.action,
                        event.resource_type,
                        event.resource_id,
                        json.dumps(event.detail, default=str),
                    ]
                ],
                column_names=self._COLUMNS,
            )
        except Exception as exc:  # noqa: BLE001
            log.error(
                "govcon_audit_insert_failed",
                error=str(exc),
                action=event.action,
                resource_type=event.resource_type,
            )

    async def record_many(self, events: Iterable[AuditEvent]) -> None:
        for ev in events:
            await self.record(ev)


class NullAuditWriter:
    """In-memory writer used by tests + dev."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def record(self, event: AuditEvent) -> None:
        self.events.append(event)

    async def record_many(self, events: Iterable[AuditEvent]) -> None:
        for ev in events:
            self.events.append(ev)


_AUDIT: AuditWriter | None = None


def set_audit_for_tests(writer: AuditWriter) -> None:
    global _AUDIT
    _AUDIT = writer


def get_audit() -> AuditWriter:
    if _AUDIT is None:
        raise RuntimeError(
            "Audit writer not initialised — call set_audit_for_tests in unit tests "
            "or trigger lifespan startup in the FastAPI app."
        )
    return _AUDIT
