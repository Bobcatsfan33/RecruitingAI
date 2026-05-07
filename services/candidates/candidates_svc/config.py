"""Service configuration loaded from environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql://wfi:wfi@localhost:5432/workforce_intelligence",
        alias="DATABASE_URL",
    )
    clickhouse_url: str = Field(default="http://localhost:8123", alias="CLICKHOUSE_URL")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    voyage_api_key: str | None = Field(default=None, alias="VOYAGE_API_KEY")
    apollo_api_key: str | None = Field(default=None, alias="APOLLO_API_KEY")
    rules_service_url: str = Field(
        default="http://localhost:8001", alias="RULES_SERVICE_URL"
    )
    port: int = Field(default=8000, alias="PORT_CANDIDATES")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
