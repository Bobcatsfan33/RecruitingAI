"""Redis client + in-memory test double for sync state."""

from __future__ import annotations

import threading
from typing import Any, Protocol


class RedisLike(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...
    async def delete(self, key: str) -> None: ...


class RealRedis:
    def __init__(self, url: str):
        import redis.asyncio as redis

        self._client = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str) -> None:
        await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def close(self) -> None:
        await self._client.aclose()


class InMemoryRedis:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lock = threading.Lock()

    async def get(self, key: str) -> str | None:
        with self._lock:
            return self._store.get(key)

    async def set(self, key: str, value: str) -> None:
        with self._lock:
            self._store[key] = value

    async def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)


_REDIS: RedisLike | None = None


def set_redis_for_tests(client: RedisLike) -> None:
    global _REDIS
    _REDIS = client


def get_redis() -> RedisLike:
    if _REDIS is None:
        raise RuntimeError("Redis client not initialised")
    return _REDIS


def init_redis(url: str) -> RedisLike:
    """Construct + register a real client for app startup."""
    global _REDIS
    _REDIS = RealRedis(url)
    return _REDIS


def init_in_memory() -> InMemoryRedis:
    global _REDIS
    client = InMemoryRedis()
    _REDIS = client
    return client


def _to_protocol(client: Any) -> RedisLike:  # pragma: no cover — type checker satisfier
    return client
