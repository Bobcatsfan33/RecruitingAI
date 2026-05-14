"""Shared fixtures for govcon-wfi tests."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from govcon_wfi.db import InMemoryDatabase, set_database_for_tests
from govcon_wfi.deps import NullAuditWriter, set_audit_for_tests
from govcon_wfi.embeddings import NullEmbeddingProvider, set_embedder_for_tests
from govcon_wfi.redis_client import init_in_memory


@pytest.fixture
def db() -> InMemoryDatabase:
    store = InMemoryDatabase()
    set_database_for_tests(store)
    return store


@pytest.fixture
def audit() -> NullAuditWriter:
    writer = NullAuditWriter()
    set_audit_for_tests(writer)
    return writer


@pytest.fixture(autouse=True)
def _redis_inmemory():
    init_in_memory()


@pytest.fixture(autouse=True)
def _embedder_null():
    set_embedder_for_tests(NullEmbeddingProvider())


@pytest.fixture
def app(db: InMemoryDatabase, audit: NullAuditWriter) -> FastAPI:
    # Build the FastAPI app without going through lifespan (which would hit
    # real Postgres/Redis). The autouse fixtures already set up in-memory
    # backing.
    from fastapi import FastAPI

    app = FastAPI(title="GovCon Workforce Intelligence (test)", version="1.0.0")
    from govcon_wfi.routers import admin, contracts, employees, health
    from govcon_wfi.routers.placeholders import (
        alerts_router,
        auth_router,
        bench_router,
        gaps_router,
        lcats_router,
        recompetes_router,
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


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
