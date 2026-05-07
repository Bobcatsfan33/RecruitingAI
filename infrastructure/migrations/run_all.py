"""Run every PG + ClickHouse migration from disk in order.

Idempotent. Safe to invoke from `make migrate`, CI, or production deploy
hooks. Refuses to apply a partial migration: each .sql file runs in its own
transaction (PG) or single statement (CH).
"""

from __future__ import annotations

import os
import pathlib
import sys
from typing import Iterable

import psycopg
import requests

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PG_INIT = REPO_ROOT / "infrastructure" / "schema" / "init"
CH_DIR = REPO_ROOT / "infrastructure" / "migrations" / "clickhouse"


def _ordered_sql_files(directory: pathlib.Path) -> Iterable[pathlib.Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.suffix == ".sql")


def _apply_postgres(database_url: str) -> None:
    files = list(_ordered_sql_files(PG_INIT))
    if not files:
        print("[pg] no migrations found")
        return
    print(f"[pg] applying {len(files)} files against {_redact(database_url)}")
    with psycopg.connect(database_url, autocommit=False) as conn:
        for path in files:
            sql = path.read_text()
            print(f"[pg] -> {path.name}")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
    print("[pg] done")


def _apply_clickhouse(url: str, database: str) -> None:
    files = list(_ordered_sql_files(CH_DIR))
    if not files:
        print("[ch] no migrations found")
        return
    print(f"[ch] applying {len(files)} files against {url}")
    for path in files:
        sql = path.read_text()
        # First file creates the database; rest run with that database as default.
        params = {} if path.name.startswith("01_") else {"database": database}
        print(f"[ch] -> {path.name}")
        for statement in _split_statements(sql):
            response = requests.post(
                url,
                params=params,
                data=statement.encode(),
                timeout=30,
                auth=_clickhouse_auth(),
            )
            if response.status_code >= 400:
                raise RuntimeError(f"ClickHouse error on {path.name}: {response.text}")
    print("[ch] done")


def _split_statements(sql: str) -> Iterable[str]:
    """ClickHouse's HTTP interface accepts only one statement per request."""
    for raw in sql.split(";"):
        stripped = raw.strip()
        if stripped:
            yield stripped


def _clickhouse_auth():
    user = os.environ.get("CLICKHOUSE_USER", "default")
    password = os.environ.get("CLICKHOUSE_PASSWORD", "")
    if user or password:
        return (user, password)
    return None


def _redact(url: str) -> str:
    if "@" in url:
        head, tail = url.split("@", 1)
        if "://" in head:
            scheme, _ = head.split("://", 1)
            return f"{scheme}://***@{tail}"
    return url


def main() -> int:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://wfi:wfi@localhost:5432/workforce_intelligence",
    )
    clickhouse_url = os.environ.get("CLICKHOUSE_URL", "http://localhost:8123")
    clickhouse_db = os.environ.get("CLICKHOUSE_DATABASE", "workforce_analytics")
    _apply_postgres(database_url)
    _apply_clickhouse(clickhouse_url, clickhouse_db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
