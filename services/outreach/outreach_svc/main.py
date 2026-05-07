"""Outreach + Close Protection FastAPI surface.

POST /v1/outreach/render        — render a single template (debug)
POST /v1/outreach/sequence/start — materialise a sequence for a candidate
POST /v1/outreach/send           — send one message via configured channel
POST /v1/outreach/classify       — classify a candidate reply
POST /v1/outreach/ab/record      — record an A/B sample
GET  /v1/outreach/ab/{key}       — current significance result
POST /v1/close/start             — kick off close-protection workflow
POST /v1/close/response          — feed a reply into close-protection
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

from outreach_svc.ab import Experiment, evaluate
from outreach_svc.channels import OutreachMessage, select_channel
from outreach_svc.classifier import classify, classify_heuristic
from outreach_svc.close_protection import CloseProtectionAgent
from outreach_svc.sequences import (
    SEQUENCES,
    StepInstance,
    materialise,
    next_step,
    stop_on_response,
)
from outreach_svc.templates import TemplateContext, render
from wfi_audit import AuditLogger, NullAuditLogger
from wfi_events import EventPublisher, NullEventPublisher
from wfi_llm import ModelRouter, NullModelRouter

log = structlog.get_logger("outreach")
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


def _build_router():
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ModelRouter()
        except RuntimeError as exc:
            log.warning("router_init_failed", error=str(exc))
    return NullModelRouter(response_text='{"label": "unknown", "confidence": 0.5, "reasoning": ""}')


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    audit = _build_audit()
    events = _build_events()
    router = _build_router()
    _state["audit"] = audit
    _state["events"] = events
    _state["router"] = router
    _state["close_protection"] = CloseProtectionAgent(
        audit=audit, events=events, router=router,
    )
    _state["experiments"] = {}
    log.info("outreach_service_started")
    yield


app = FastAPI(title="WFI Outreach", version="0.1.0", lifespan=lifespan)


# --- request models -------------------------------------------------------

class RenderRequest(BaseModel):
    template_id: str
    context: TemplateContext


class SequenceStartRequest(BaseModel):
    sequence_key: str = Field(default="precision_outreach")
    candidate_id: UUID
    started_at: datetime | None = None


class SendRequest(BaseModel):
    channel: str = "email"
    to: str
    template_id: str
    context: TemplateContext


class ClassifyRequest(BaseModel):
    reply_text: str
    use_llm_fallback: bool = True


class AbRecordRequest(BaseModel):
    experiment_key: str
    arm: str
    responded: bool


class CloseStartRequest(BaseModel):
    candidate_id: UUID
    requisition_id: UUID | None = None
    accepted_at: datetime | None = None


class CloseResponseRequest(BaseModel):
    candidate_id: UUID
    requisition_id: UUID | None = None
    instance_state: list[dict[str, Any]] | None = None
    reply_text: str


# --- routes --------------------------------------------------------------

@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/outreach/render")
async def render_template(req: RenderRequest) -> dict[str, str]:
    try:
        return render(req.template_id, req.context)
    except KeyError:
        raise HTTPException(404, f"unknown template {req.template_id}")


@app.post("/v1/outreach/sequence/start")
async def start_sequence(req: SequenceStartRequest) -> list[dict[str, Any]]:
    sequence = SEQUENCES.get(req.sequence_key)
    if not sequence:
        raise HTTPException(404, f"unknown sequence {req.sequence_key}")
    instances = materialise(sequence, started_at=req.started_at)
    return [_instance_to_dict(i) for i in instances]


@app.post("/v1/outreach/send")
async def send(req: SendRequest) -> dict[str, Any]:
    rendered = render(req.template_id, req.context)
    channel = select_channel(req.channel)
    msg = OutreachMessage(
        to=req.to,
        subject=rendered["subject"],
        body_text=rendered["body_text"],
    )
    result = await channel.send(msg)
    return {
        "success": result.success,
        "provider": result.provider,
        "channel": result.channel,
        "message_id": result.message_id,
        "error": result.error,
    }


@app.post("/v1/outreach/classify")
async def classify_endpoint(req: ClassifyRequest) -> dict[str, Any]:
    if req.use_llm_fallback:
        result = await classify(req.reply_text, router=_state["router"])
    else:
        result = classify_heuristic(req.reply_text)
    return {
        "label": result.label,
        "confidence": result.confidence,
        "method": result.method,
        "reasoning": result.reasoning,
    }


@app.post("/v1/outreach/ab/record")
async def ab_record(req: AbRecordRequest) -> dict[str, Any]:
    experiments: dict[str, Experiment] = _state["experiments"]
    exp = experiments.setdefault(req.experiment_key, Experiment(key=req.experiment_key))
    exp.record(req.arm, responded=req.responded)
    sig = evaluate(exp)
    return {
        "experiment": req.experiment_key,
        "arms": {a.name: {"sent": a.sent, "responded": a.responded} for a in exp.arms.values()},
        "significance": sig.__dict__ if sig else None,
    }


@app.get("/v1/outreach/ab/{key}")
async def ab_status(key: str) -> dict[str, Any]:
    exp = _state["experiments"].get(key)
    if exp is None:
        raise HTTPException(404, "experiment not found")
    sig = evaluate(exp)
    return {
        "experiment": key,
        "arms": {a.name: {"sent": a.sent, "responded": a.responded} for a in exp.arms.values()},
        "significance": sig.__dict__ if sig else None,
    }


@app.post("/v1/close/start")
async def close_start(req: CloseStartRequest) -> list[dict[str, Any]]:
    agent: CloseProtectionAgent = _state["close_protection"]
    instances = agent.activate(started_at=req.accepted_at)
    return [_instance_to_dict(i) for i in instances]


@app.post("/v1/close/response")
async def close_response(req: CloseResponseRequest) -> dict[str, Any]:
    agent: CloseProtectionAgent = _state["close_protection"]
    instances = _instances_from_state(req.instance_state or [])
    classification = await agent.handle_response(
        instances,
        candidate_id=req.candidate_id,
        requisition_id=req.requisition_id,
        reply_text=req.reply_text,
    )
    return {
        "classification": classification,
        "instances": [_instance_to_dict(i) for i in instances],
    }


def _instance_to_dict(i: StepInstance) -> dict[str, Any]:
    return {
        "key": i.step.key,
        "channel": i.step.channel,
        "template_id": i.step.template_id,
        "fire_at": i.fire_at.isoformat(),
        "status": i.status,
        "response": i.response,
        "skipped_reason": i.skipped_reason,
    }


def _instances_from_state(rows: list[dict[str, Any]]) -> list[StepInstance]:
    """Rebuild StepInstances from the dict shape we returned earlier.
    The HTTP boundary is stateless; clients persist their own state."""
    from outreach_svc.sequences import CLOSE_PROTECTION, Step

    out: list[StepInstance] = []
    for row in rows:
        step = next(
            (s for s in CLOSE_PROTECTION.steps if s.key == row.get("key")),
            Step(
                key=row.get("key", ""),
                channel=row.get("channel", "email"),
                template_id=row.get("template_id", ""),
                offset_hours=0,
            ),
        )
        out.append(
            StepInstance(
                step=step,
                fire_at=datetime.fromisoformat(row["fire_at"]),
                status=row.get("status", "pending"),
                response=row.get("response"),
                skipped_reason=row.get("skipped_reason"),
            )
        )
    return out
