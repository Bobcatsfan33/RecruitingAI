"""GovCon Workforce Intelligence — unified FastAPI app."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from govcon_wfi.config import Settings
from govcon_wfi.db import Database, set_database_for_tests
from govcon_wfi.deps.audit import (
    ClickHouseAuditWriter,
    NullAuditWriter,
    set_audit_for_tests,
)
from govcon_wfi.redis_client import init_in_memory, init_redis
from govcon_wfi.routers import admin, contracts, employees, health
from govcon_wfi.routers.placeholders import (
    alerts_router,
    auth_router,
    bench_router,
    gaps_router,
    lcats_router,
    recompetes_router,
)
from govcon_wfi.sched.scheduler import IngestScheduler

log = structlog.get_logger("govcon.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level)

    db: Database | None = None
    try:
        db = Database(settings.database_url)
        await db.connect()
        set_database_for_tests(db)
    except Exception as exc:  # noqa: BLE001
        log.warning("database_unreachable_using_inmemory", error=str(exc))
        from govcon_wfi.db import InMemoryDatabase

        set_database_for_tests(InMemoryDatabase())

    init_redis(settings.redis_url) if not _starts_with_dummy(settings.redis_url) else init_in_memory()

    if settings.enable_real_ingestors:
        try:
            set_audit_for_tests(ClickHouseAuditWriter.from_env())
        except Exception as exc:  # noqa: BLE001
            log.warning("audit_clickhouse_unreachable", error=str(exc))
            set_audit_for_tests(NullAuditWriter())
    else:
        set_audit_for_tests(NullAuditWriter())

    scheduler: IngestScheduler | None = None
    if settings.enable_scheduler:
        scheduler = IngestScheduler(settings)
        scheduler.start()

    log.info("govcon_wfi_started")
    try:
        yield
    finally:
        if scheduler:
            scheduler.shutdown()
        if db:
            await db.close()
        log.info("govcon_wfi_shutdown")


def _starts_with_dummy(url: str) -> bool:
    return url.startswith("memory://") or url == ""


def create_app() -> FastAPI:
    app = FastAPI(
        title="GovCon Workforce Intelligence",
        description="Contract intelligence + workforce gap analysis for GovCon services firms",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(contracts.router)
    app.include_router(employees.router)
    app.include_router(admin.router)
    app.include_router(recompetes_router)
    app.include_router(lcats_router)
    app.include_router(gaps_router)
    app.include_router(bench_router)
    app.include_router(alerts_router)
    app.include_router(auth_router)
    return app


app = create_app()
