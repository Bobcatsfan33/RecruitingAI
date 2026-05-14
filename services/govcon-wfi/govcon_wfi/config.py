"""Service configuration loaded from env."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    redis_url: str
    clickhouse_url: str
    sam_gov_api_key: str | None
    enable_real_ingestors: bool
    enable_scheduler: bool
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get(
                "DATABASE_URL",
                "postgresql://wfi:wfi@localhost:5432/workforce_intelligence",
            ),
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            clickhouse_url=os.environ.get("CLICKHOUSE_URL", "http://localhost:8123"),
            sam_gov_api_key=os.environ.get("SAM_GOV_API_KEY"),
            enable_real_ingestors=_bool(os.environ.get("ENABLE_REAL_INGESTORS", "false")),
            enable_scheduler=_bool(os.environ.get("ENABLE_SCHEDULER", "false")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )


def _bool(v: str | None) -> bool:
    return (v or "").lower() in {"1", "true", "yes", "on"}
