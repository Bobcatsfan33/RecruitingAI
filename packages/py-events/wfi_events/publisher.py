"""Dual-write event publisher (ClickHouse + Redis Streams)."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

import clickhouse_connect
import redis.asyncio as redis
import structlog
from clickhouse_connect.driver.client import Client
from wfi_schemas import InteractionEvent

log = structlog.get_logger("wfi.events")

CLICKHOUSE_TABLE = "interaction_events"
STREAM_PREFIX = "agent_events:"

_COLUMNS = [
    "event_id",
    "timestamp",
    "event_type",
    "candidate_id",
    "requisition_id",
    "client_id",
    "agent_type",
    "channel",
    "metadata",
    "outcome",
    "cost_usd",
    "duration_seconds",
]


def _row(event: InteractionEvent) -> list[Any]:
    return [
        event.event_id,
        event.timestamp,
        event.event_type,
        event.candidate_id,
        event.requisition_id,
        event.client_id,
        event.agent_type,
        event.channel,
        json.dumps(event.metadata, default=str),
        event.outcome,
        event.cost_usd,
        event.duration_seconds,
    ]


class EventPublisher:
    def __init__(
        self,
        *,
        clickhouse: Client,
        redis_client: redis.Redis,
        database: str = "workforce_analytics",
    ) -> None:
        self._ch = clickhouse
        self._redis = redis_client
        self._database = database

    @classmethod
    def from_env(cls) -> EventPublisher:
        ch_url = os.environ.get("CLICKHOUSE_URL", "http://localhost:8123")
        parsed = urlparse(ch_url)
        ch = clickhouse_connect.get_client(
            host=parsed.hostname or "localhost",
            port=parsed.port or 8123,
            username=os.environ.get("CLICKHOUSE_USER", "default"),
            password=os.environ.get("CLICKHOUSE_PASSWORD", ""),
            database=os.environ.get("CLICKHOUSE_DATABASE", "workforce_analytics"),
        )
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
        return cls(clickhouse=ch, redis_client=r)

    async def publish(self, event: InteractionEvent) -> None:
        await asyncio.gather(
            self._write_clickhouse(event),
            self._write_redis(event),
        )

    async def publish_many(self, events: Iterable[InteractionEvent]) -> None:
        events = list(events)
        if not events:
            return
        await asyncio.gather(
            self._write_clickhouse_many(events),
            *(self._write_redis(e) for e in events),
        )

    async def _write_clickhouse(self, event: InteractionEvent) -> None:
        try:
            await asyncio.to_thread(
                self._ch.insert,
                f"{self._database}.{CLICKHOUSE_TABLE}",
                [_row(event)],
                column_names=_COLUMNS,
            )
        except Exception as exc:
            log.error("ch_insert_failed", error=str(exc), event_type=event.event_type)

    async def _write_clickhouse_many(self, events: list[InteractionEvent]) -> None:
        try:
            await asyncio.to_thread(
                self._ch.insert,
                f"{self._database}.{CLICKHOUSE_TABLE}",
                [_row(e) for e in events],
                column_names=_COLUMNS,
            )
        except Exception as exc:
            log.error("ch_insert_failed_batch", error=str(exc), count=len(events))

    async def _write_redis(self, event: InteractionEvent) -> None:
        try:
            stream = f"{STREAM_PREFIX}{event.agent_type}"
            await self._redis.xadd(
                stream,
                {"data": event.model_dump_json()},
                maxlen=100_000,
                approximate=True,
            )
        except Exception as exc:
            log.error("redis_xadd_failed", error=str(exc), agent=event.agent_type)


class NullEventPublisher:
    """Test double — captures events in memory."""

    def __init__(self):
        self.events: list[InteractionEvent] = []

    async def publish(self, event: InteractionEvent) -> None:
        self.events.append(event)

    async def publish_many(self, events: Iterable[InteractionEvent]) -> None:
        self.events.extend(events)
