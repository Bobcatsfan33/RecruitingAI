"""Postgres connection pool + low-level helpers shared by the repos."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

import psycopg
from psycopg_pool import AsyncConnectionPool

from candidates_svc.config import get_settings

_pool: AsyncConnectionPool | None = None


async def init_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = AsyncConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=10,
            open=False,
        )
        await _pool.open()
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@contextlib.asynccontextmanager
async def acquire() -> AsyncIterator[psycopg.AsyncConnection]:
    pool = await init_pool()
    async with pool.connection() as conn:
        yield conn
