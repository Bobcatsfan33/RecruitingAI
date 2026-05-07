"""Client Advisory + Development FastAPI surface.

POST /v1/advisory/intake          — feasibility report on a new req
POST /v1/advisory/stalled         — stalled-pipeline diagnosis
POST /v1/development/scan         — pull careers feed for a client
POST /v1/development/recompete    — build a recompete trigger
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import structlog
from fastapi import FastAPI
from pydantic import BaseModel

from client_advisory_svc.development import (
    DevelopmentReport,
    OutreachTrigger,
    scan_careers_feed,
    synthesize_recompete_trigger,
)
from client_advisory_svc.intake import FeasibilityReport, analyze
from client_advisory_svc.stalled import diagnose
from wfi_rules_sdk import MockRulesClient, RulesClient
from wfi_schemas import Requisition

log = structlog.get_logger("client_advisory")


def _build_rules():
    if os.environ.get("OPA_URL") or os.environ.get("RULES_SERVICE_URL"):
        try:
            return RulesClient.from_env()
        except Exception as exc:  # noqa: BLE001
            log.warning("rules_client_init_failed", error=str(exc))
    return MockRulesClient()


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    _state["rules"] = _build_rules()
    log.info("client_advisory_started")
    yield


app = FastAPI(title="WFI Client Advisory", version="0.1.0", lifespan=lifespan)


class IntakeRequest(BaseModel):
    requisition: Requisition
    market_lookup: dict[str, Any] | None = None


class StalledRequest(BaseModel):
    events: list[dict[str, Any]]


class CareersScanRequest(BaseModel):
    client_id: str | None = None
    client_name: str
    feed_url: str


class RecompeteRequest(BaseModel):
    client_id: str | None = None
    client_name: str
    contract_name: str
    period_end: datetime


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/advisory/intake")
async def advisory_intake(req: IntakeRequest) -> FeasibilityReport:
    return await analyze(req.requisition, rules=_state["rules"], market_lookup=req.market_lookup)


@app.post("/v1/advisory/stalled")
async def advisory_stalled(req: StalledRequest) -> dict[str, Any]:
    diagnosis = diagnose(req.events)
    return diagnosis.__dict__


@app.post("/v1/development/scan")
async def development_scan(req: CareersScanRequest) -> dict[str, Any]:
    triggers = await scan_careers_feed(
        client_id=req.client_id,
        client_name=req.client_name,
        feed_url=req.feed_url,
    )
    report = DevelopmentReport(
        client_id=req.client_id,
        client_name=req.client_name,
        triggers=triggers,
        summary=f"{len(triggers)} triggers found in careers feed",
    )
    return report.to_dict()


@app.post("/v1/development/recompete")
async def development_recompete(req: RecompeteRequest) -> dict[str, Any]:
    trigger: OutreachTrigger = synthesize_recompete_trigger(
        client_id=req.client_id,
        client_name=req.client_name,
        contract_name=req.contract_name,
        period_end=req.period_end,
    )
    return trigger.__dict__
