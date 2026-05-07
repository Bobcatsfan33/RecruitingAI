"""Market intelligence FastAPI surface — the data API for subscribers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import structlog
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from market_svc.comp import CompBenchmark, CompPoint, benchmarks
from market_svc.competitive import (
    CompetitiveAssessment,
    CompetitiveSignals,
    evaluate as competitive_evaluate,
)
from market_svc.velocity import HiringSignal, VelocityReport, report as velocity_report

log = structlog.get_logger("market")

# Static API tier table. Production wires Stripe to populate dynamically.
TIER_RATE_LIMIT = {
    "free": 60,
    "pro": 600,
    "enterprise": 6000,
}


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # In-memory subscription registry for dev. Production reads from PG.
    _state["subscriptions"] = {"dev-key": "enterprise"}
    log.info("market_service_started")
    yield


app = FastAPI(title="WFI Market Intelligence", version="0.1.0", lifespan=lifespan)


class CompBenchmarkRequest(BaseModel):
    points: list[CompPoint]
    w2_only: bool = True


class VelocityRequest(BaseModel):
    signals: list[HiringSignal]
    now: datetime | None = None


class CompetitiveRequest(BaseModel):
    signals: CompetitiveSignals


def _require_subscription(api_key: str | None) -> str:
    if not api_key:
        raise HTTPException(401, "X-Api-Key header required")
    tier = _state["subscriptions"].get(api_key)
    if not tier:
        raise HTTPException(403, "unknown api key")
    return tier


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/market/tier")
async def my_tier(x_api_key: str | None = Header(default=None)) -> dict[str, Any]:
    tier = _require_subscription(x_api_key)
    return {"tier": tier, "rate_limit_per_minute": TIER_RATE_LIMIT[tier]}


@app.post("/v1/market/comp/benchmarks")
async def comp_benchmarks(
    req: CompBenchmarkRequest,
    x_api_key: str | None = Header(default=None),
) -> list[CompBenchmark]:
    _require_subscription(x_api_key)
    return benchmarks(req.points, w2_only=req.w2_only)


@app.post("/v1/market/velocity")
async def velocity(
    req: VelocityRequest,
    x_api_key: str | None = Header(default=None),
) -> VelocityReport:
    _require_subscription(x_api_key)
    return velocity_report(req.signals, now=req.now)


@app.post("/v1/market/competitive")
async def competitive(
    req: CompetitiveRequest,
    x_api_key: str | None = Header(default=None),
) -> CompetitiveAssessment:
    _require_subscription(x_api_key)
    return competitive_evaluate(req.signals)
