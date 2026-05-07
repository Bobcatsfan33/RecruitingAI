"""Pipeline service FastAPI surface.

POST /v1/pipeline/transition         — record a stage transition + audit
GET  /v1/pipeline/{req_id}/health    — SLA + silver-pool snapshot
POST /v1/pipeline/route               — multi-req routing for a candidate
POST /v1/pipeline/silver/hold         — pin a silver medalist
POST /v1/pipeline/silver/promote      — promote rank-1 silver (after falloff)
POST /v1/pipeline/submission/build    — generate the submission package
POST /v1/pipeline/ats/submit          — push to configured ATS
GET  /v1/pipeline/ats/{external_id}   — fetch ATS status
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pipeline_svc.ats import AtsSubmission, MockAtsAdapter, select_adapter
from pipeline_svc.routing import CandidateView, RequisitionView, route
from pipeline_svc.silver import SilverPool
from pipeline_svc.sla import StageHealth, evaluate as sla_evaluate
from pipeline_svc.state import Stage, can_transition
from pipeline_svc.submission_package import generate, to_dict
from wfi_audit import AuditLogger, NullAuditLogger
from wfi_events import EventPublisher, NullEventPublisher
from wfi_schemas import ActionType, AuditLogEntry, Candidate, Requisition, Scorecard

log = structlog.get_logger("pipeline")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))


def _build_audit():
    if os.environ.get("CLICKHOUSE_URL"):
        try:
            return AuditLogger.from_env()
        except Exception as exc:  # noqa: BLE001
            log.warning("audit_init_failed", error=str(exc))
    return NullAuditLogger()


def _build_events():
    if os.environ.get("CLICKHOUSE_URL"):
        try:
            return EventPublisher.from_env()
        except Exception as exc:  # noqa: BLE001
            log.warning("events_init_failed", error=str(exc))
    return NullEventPublisher()


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    _state["audit"] = _build_audit()
    _state["events"] = _build_events()
    _state["silver"] = SilverPool()
    _state["ats"] = select_adapter()
    log.info("pipeline_service_started", ats=_state["ats"].name)
    yield


app = FastAPI(title="WFI Pipeline", version="0.1.0", lifespan=lifespan)


class TransitionRequest(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    from_stage: Stage
    to_stage: Stage
    reason: str = ""


class RouteRequest(BaseModel):
    candidate: CandidateView
    reqs: list[RequisitionView]
    score_floor: float = 0.65
    limit: int = 10


class SilverHoldRequest(BaseModel):
    requisition_id: UUID
    candidate_id: UUID
    rank: int | None = None


class SilverPromoteRequest(BaseModel):
    requisition_id: UUID


class SubmissionBuildRequest(BaseModel):
    candidate: Candidate
    requisition: Requisition
    scorecard: Scorecard


class AtsSubmitRequest(BaseModel):
    candidate_email: str
    candidate_first_name: str
    candidate_last_name: str
    job_id: str
    notes: str = ""


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/pipeline/transition")
async def transition(req: TransitionRequest) -> dict[str, Any]:
    if not can_transition(req.from_stage, req.to_stage):
        raise HTTPException(
            409,
            f"transition {req.from_stage} -> {req.to_stage} is not allowed",
        )
    audit: AuditLogger = _state["audit"]
    await audit.record(
        AuditLogEntry(
            action_type=ActionType.ROUTING_DECISION,
            candidate_id=req.candidate_id,
            requisition_id=req.requisition_id,
            agent_type="pipeline_manager",
            model_used="state_machine",
            input_summary=f"{req.from_stage} -> {req.to_stage}",
            decision=str(req.to_stage),
            reasoning=req.reason or "stage advance",
            confidence_score=1.0,
        )
    )
    return {"from_stage": req.from_stage, "to_stage": req.to_stage, "ok": True}


@app.get("/v1/pipeline/{req_id}/health")
async def pipeline_health(
    req_id: UUID,
    stage: Stage = Stage.SCREENING,
    entered_at: datetime | None = None,
) -> dict[str, Any]:
    silver: SilverPool = _state["silver"]
    sh: StageHealth = sla_evaluate(stage, entered_at or datetime.utcnow())
    return {
        "requisition_id": str(req_id),
        "stage_health": sh.__dict__,
        "silver_pool": silver.health(req_id),
    }


@app.post("/v1/pipeline/route")
async def pipeline_route(req: RouteRequest) -> list[dict[str, Any]]:
    matches = route(req.candidate, req.reqs, score_floor=req.score_floor, limit=req.limit)
    return [m.__dict__ for m in matches]


@app.post("/v1/pipeline/silver/hold")
async def silver_hold(req: SilverHoldRequest) -> dict[str, Any]:
    silver: SilverPool = _state["silver"]
    entry = silver.hold(req.requisition_id, req.candidate_id, rank=req.rank)
    return {
        "requisition_id": str(entry.requisition_id),
        "candidate_id": str(entry.candidate_id),
        "rank": entry.rank,
    }


@app.post("/v1/pipeline/silver/promote")
async def silver_promote(req: SilverPromoteRequest) -> dict[str, Any]:
    silver: SilverPool = _state["silver"]
    promoted = silver.promote_next(req.requisition_id)
    if not promoted:
        raise HTTPException(404, "no silver medalists available")
    audit: AuditLogger = _state["audit"]
    await audit.record(
        AuditLogEntry(
            action_type=ActionType.ROUTING_DECISION,
            candidate_id=promoted.candidate_id,
            requisition_id=req.requisition_id,
            agent_type="pipeline_manager",
            model_used="silver_pool",
            decision="promote_silver",
            reasoning="primary candidate fell off; promoting backup",
            confidence_score=1.0,
        )
    )
    return {
        "requisition_id": str(promoted.requisition_id),
        "candidate_id": str(promoted.candidate_id),
        "promoted_at": promoted.promoted_at.isoformat() if promoted.promoted_at else None,
    }


@app.post("/v1/pipeline/submission/build")
async def submission_build(req: SubmissionBuildRequest) -> dict[str, Any]:
    pkg = generate(req.candidate, req.requisition, req.scorecard)
    return to_dict(pkg)


@app.post("/v1/pipeline/ats/submit")
async def ats_submit(req: AtsSubmitRequest) -> dict[str, Any]:
    adapter = _state["ats"]
    submission = AtsSubmission(
        candidate_email=req.candidate_email,
        candidate_first_name=req.candidate_first_name,
        candidate_last_name=req.candidate_last_name,
        job_id=req.job_id,
        notes=req.notes,
    )
    result = await adapter.submit(submission)
    return {
        "success": result.success,
        "provider": result.provider,
        "external_id": result.external_id,
        "url": result.url,
        "error": result.error,
    }


@app.get("/v1/pipeline/ats/{external_id}")
async def ats_status(external_id: str) -> dict[str, Any]:
    adapter = _state["ats"]
    return await adapter.fetch_status(external_id)
