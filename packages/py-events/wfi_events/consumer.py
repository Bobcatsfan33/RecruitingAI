"""Long-running Redis Streams consumer used by the Pipeline Manager and
Outcome Loops services."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as redis
import structlog
from redis.exceptions import ResponseError

log = structlog.get_logger("wfi.events.consumer")

Handler = Callable[[dict[str, Any], str], Awaitable[None]]


class RedisStreamConsumer:
    """Consumer-group reader with at-least-once delivery + DLQ on handler error."""

    def __init__(
        self,
        *,
        redis_client: redis.Redis,
        stream: str,
        group: str,
        consumer: str,
        batch_size: int = 10,
        block_ms: int = 5000,
    ) -> None:
        self._redis = redis_client
        self._stream = stream
        self._group = group
        self._consumer = consumer
        self._batch_size = batch_size
        self._block_ms = block_ms
        self._running = True

    @classmethod
    def from_env(cls, *, stream: str, group: str, consumer: str, **kwargs: Any) -> RedisStreamConsumer:
        client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
        return cls(redis_client=client, stream=stream, group=group, consumer=consumer, **kwargs)

    def stop(self) -> None:
        self._running = False

    async def consume(self, handler: Handler) -> None:
        await self._ensure_group()
        while self._running:
            try:
                response = await self._redis.xreadgroup(
                    groupname=self._group,
                    consumername=self._consumer,
                    streams={self._stream: ">"},
                    count=self._batch_size,
                    block=self._block_ms,
                )
            except ResponseError as exc:
                log.error("xreadgroup_failed", error=str(exc), stream=self._stream)
                await asyncio.sleep(1)
                continue
            if not response:
                continue
            for _stream_bytes, entries in response:
                for msg_id, fields in entries:
                    msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                    raw = fields.get(b"data") if isinstance(fields, dict) else None
                    if raw is None:
                        await self._redis.xack(self._stream, self._group, msg_id_str)
                        continue
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        log.warning("malformed_event", stream=self._stream, msg_id=msg_id_str)
                        await self._redis.xack(self._stream, self._group, msg_id_str)
                        continue
                    try:
                        await handler(payload, msg_id_str)
                        await self._redis.xack(self._stream, self._group, msg_id_str)
                    except Exception as exc:
                        log.error(
                            "handler_failed",
                            error=str(exc),
                            stream=self._stream,
                            msg_id=msg_id_str,
                        )
                        await self._redis.xadd(
                            f"dlq:{self._stream}",
                            {"data": raw, "error": str(exc)},
                        )
                        await self._redis.xack(self._stream, self._group, msg_id_str)

    async def _ensure_group(self) -> None:
        try:
            await self._redis.xgroup_create(self._stream, self._group, id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
