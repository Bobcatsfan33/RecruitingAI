"""Postgres pool wrapper + in-memory test double.

Both implement ``DatabaseProtocol`` so routers can be unit-tested without a
running Postgres instance. The in-memory backing store mirrors only what the
API layer needs — enough to round-trip CRUD calls and run search filters.
"""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from typing import Any, Protocol
from uuid import UUID, uuid4

import structlog

log = structlog.get_logger("govcon.db")


class DatabaseProtocol(Protocol):
    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]: ...
    async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any] | None: ...
    async def execute(self, sql: str, *args: Any) -> str: ...
    async def insert_returning(
        self, table: str, columns: list[str], values: list[Any]
    ) -> dict[str, Any]: ...
    async def update_returning(
        self,
        table: str,
        pk_column: str,
        pk_value: Any,
        columns: list[str],
        values: list[Any],
    ) -> dict[str, Any] | None: ...
    async def list_rows(
        self,
        table: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]: ...
    async def get_row(self, table: str, pk_column: str, pk_value: Any) -> dict[str, Any] | None: ...


class Database:
    """Real asyncpg-backed pool. Lazy-loaded so import never touches the DB."""

    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: Any = None

    async def connect(self) -> None:
        if self._pool is not None:
            return
        import asyncpg  # noqa: PLC0415 — defer import to keep tests light

        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Any]:
        await self.connect()
        async with self._pool.acquire() as conn:
            yield conn

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        async with self.acquire() as conn:
            rows = await conn.fetch(sql, *args)
            return [dict(r) for r in rows]

    async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any] | None:
        async with self.acquire() as conn:
            row = await conn.fetchrow(sql, *args)
            return dict(row) if row else None

    async def execute(self, sql: str, *args: Any) -> str:
        async with self.acquire() as conn:
            return await conn.execute(sql, *args)

    async def insert_returning(
        self, table: str, columns: list[str], values: list[Any]
    ) -> dict[str, Any]:
        cols = ", ".join(f'"{c}"' for c in columns)
        placeholders = ", ".join(f"${i + 1}" for i in range(len(values)))
        sql = f'INSERT INTO "{table}" ({cols}) VALUES ({placeholders}) RETURNING *'  # noqa: S608
        row = await self.fetchrow(sql, *values)
        if row is None:
            raise RuntimeError(f"insert into {table} returned no row")
        return row

    async def update_returning(
        self,
        table: str,
        pk_column: str,
        pk_value: Any,
        columns: list[str],
        values: list[Any],
    ) -> dict[str, Any] | None:
        if not columns:
            return await self.get_row(table, pk_column, pk_value)
        set_clause = ", ".join(f'"{c}" = ${i + 1}' for i, c in enumerate(columns))
        pk_placeholder = f"${len(columns) + 1}"
        sql = (  # noqa: S608
            f'UPDATE "{table}" SET {set_clause}, "updated_at" = NOW() '
            f'WHERE "{pk_column}" = {pk_placeholder} RETURNING *'
        )
        return await self.fetchrow(sql, *values, pk_value)

    async def list_rows(
        self,
        table: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        args: list[Any] = []
        for col, val in (filters or {}).items():
            args.append(val)
            clauses.append(f'"{col}" = ${len(args)}')
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        order = f' ORDER BY "{order_by}" DESC' if order_by else ""
        sql = (  # noqa: S608
            f'SELECT * FROM "{table}"{where}{order} '
            f"LIMIT {int(limit)} OFFSET {int(offset)}"
        )
        return await self.fetch(sql, *args)

    async def get_row(
        self, table: str, pk_column: str, pk_value: Any
    ) -> dict[str, Any] | None:
        sql = f'SELECT * FROM "{table}" WHERE "{pk_column}" = $1'  # noqa: S608
        return await self.fetchrow(sql, pk_value)


class InMemoryDatabase:
    """Lock-protected dict store used in unit tests.

    Honours just enough of the SQL contract to drive the routers — INSERT
    auto-generates UUIDs for ``id`` columns when missing, list_rows applies
    equality filters in Python, and update_returning patches the row.
    """

    def __init__(self) -> None:
        self._tables: dict[str, dict[Any, dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def reset(self) -> None:
        with self._lock:
            self._tables.clear()

    def _table(self, name: str) -> dict[Any, dict[str, Any]]:
        return self._tables.setdefault(name, {})

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:  # noqa: ARG002
        raise NotImplementedError("InMemoryDatabase does not execute raw SQL")

    async def fetchrow(self, sql: str, *args: Any) -> dict[str, Any] | None:  # noqa: ARG002
        raise NotImplementedError("InMemoryDatabase does not execute raw SQL")

    async def execute(self, sql: str, *args: Any) -> str:  # noqa: ARG002
        return "OK"

    async def insert_returning(
        self, table: str, columns: list[str], values: list[Any]
    ) -> dict[str, Any]:
        with self._lock:
            row = dict(zip(columns, values, strict=True))
            row.setdefault("id", uuid4())
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            row.setdefault("created_at", now)
            if table in {"contracts", "employees", "alert_rules"}:
                row.setdefault("updated_at", now)
            self._table(table)[row["id"]] = row
            return dict(row)

    async def update_returning(
        self,
        table: str,
        pk_column: str,
        pk_value: Any,
        columns: list[str],
        values: list[Any],
    ) -> dict[str, Any] | None:
        with self._lock:
            store = self._table(table)
            existing = next(
                (r for r in store.values() if r.get(pk_column) == pk_value), None
            )
            if existing is None:
                return None
            for col, val in zip(columns, values, strict=True):
                existing[col] = val
            from datetime import datetime, timezone

            existing["updated_at"] = datetime.now(timezone.utc)
            return dict(existing)

    async def list_rows(
        self,
        table: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows: Iterable[dict[str, Any]] = self._table(table).values()
            if filters:
                rows = [
                    r for r in rows
                    if all(r.get(k) == v for k, v in filters.items())
                ]
            rows_list = list(rows)
            if order_by:
                rows_list.sort(
                    key=lambda r: r.get(order_by) or 0, reverse=True
                )
            return [dict(r) for r in rows_list[offset : offset + limit]]

    async def get_row(
        self, table: str, pk_column: str, pk_value: Any
    ) -> dict[str, Any] | None:
        with self._lock:
            for row in self._table(table).values():
                if row.get(pk_column) == pk_value:
                    return dict(row)
            return None

    def all_rows(self, table: str) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._table(table).values()]


_DB: DatabaseProtocol | None = None


def set_database_for_tests(db: DatabaseProtocol) -> None:
    global _DB
    _DB = db


def get_database() -> DatabaseProtocol:
    if _DB is None:
        raise RuntimeError(
            "Database not initialised — call set_database_for_tests in unit tests "
            "or trigger lifespan startup in the FastAPI app."
        )
    return _DB
