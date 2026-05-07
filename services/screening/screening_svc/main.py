"""Screening agent FastAPI service.

POST /v1/screen           — single candidate vs single req
POST /v1/screen/batch     — N candidates vs one req (parallel screening)
POST /v1/calibrate        — compare agent decisions to a labelled set,
                             report agreement vs the rubric pass threshold
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from screening_svc.agent import ScreeningAgent
from wfi_audit import AuditLogger, NullAuditLogger
from wfi_llm import ModelRouter, NullModelRouter
from wfi_rules_sdk import MockRulesClient, RulesClient
from wfi_schemas import Candidate, Requisition, Scorecard

log = structlog.get_logger("screening")
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

_state: dict[str, Any] = {}


def _build_router():
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return ModelRouter()
        except RuntimeError as exc:
            log.warning("router_init_failed", error=str(exc))
    return NullModelRouter()


def _build_rules():
    if os.environ.get("OPA_URL") or os.environ.get("RULES_SERVICE_URL"):
        try:
            return RulesClient.from_env()
        except Exception as exc:  # noqa: BLE001
            log.warning("rules_client_init_failed", error=str(exc))
    return MockRulesClient()


def _build_audit():
    if os.environ.get("CLICKHOUSE_URL"):
        try:
            return AuditLogger.from_env()
        except Exception as exc:  # noqa: BLE001
            log.warning("audit_init_failed", error=str(exc))
    return NullAuditLogger()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _state["agent"] = ScreeningAgent(
        rules=_build_rules(),
        router=_build_router(),
        audit=_build_audit(),
    )
    log.info(
        "screening_service_started",
        rules=type(_state["agent"]._rules).__name__,
        router=type(_state["agent"]._router).__name__,
        audit=type(_state["agent"]._audit).__name__,
    )
    yield


app = FastAPI(title="WFI Screening", version="0.1.0", lifespan=lifespan)


class ScreenRequest(BaseModel):
    candidate: Candidate
    requisition: Requisition
    client_id: UUID | None = None
    velocity_mode: bool | None = None


class BatchScreenRequest(BaseModel):
    requisition: Requisition
    candidates: list[Candidate] = Field(default_factory=list)
    client_id: UUID | None = None
    velocity_mode: bool | None = None
    parallelism: int = Field(default=10, ge=1, le=50)


class LabelledExample(BaseModel):
    """One row of the calibration dataset.

    Each example has a candidate, the requisition, and the
    employer-supplied ground truth: should this candidate pass the rubric?
    """

    candidate: Candidate
    requisition: Requisition
    expected_qualified: bool


class CalibrationRequest(BaseModel):
    examples: list[LabelledExample]
    target_agreement: float = Field(default=0.85, ge=0.0, le=1.0)


class CalibrationReport(BaseModel):
    total: int
    agreed: int
    agreement_rate: float
    target: float
    passed_target: bool
    false_positives: int
    false_negatives: int
    per_example: list[dict[str, Any]]


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/screen")
async def screen_one(req: ScreenRequest) -> Scorecard:
    agent: ScreeningAgent = _state["agent"]
    return await agent.screen(
        req.candidate,
        req.requisition,
        client_id=req.client_id,
        velocity_mode=req.velocity_mode,
    )


@app.post("/v1/screen/batch")
async def screen_batch(req: BatchScreenRequest) -> list[Scorecard]:
    if not req.candidates:
        return []
    agent: ScreeningAgent = _state["agent"]
    sem = asyncio.Semaphore(req.parallelism)

    async def _one(candidate: Candidate) -> Scorecard:
        async with sem:
            return await agent.screen(
                candidate,
                req.requisition,
                client_id=req.client_id,
                velocity_mode=req.velocity_mode,
            )

    return await asyncio.gather(*(_one(c) for c in req.candidates))


@app.post("/v1/calibrate")
async def calibrate(body: CalibrationRequest) -> CalibrationReport:
    """Replacement for the blueprint's "85% recruiter agreement" metric.

    The employer supplies labelled examples; we compare agent qualified/
    disqualified vs `expected_qualified`. Returns the agreement rate,
    whether it crossed the configured target (default 85%), and a
    per-example breakdown for diagnostics.
    """
    if not body.examples:
        raise HTTPException(400, "no examples provided")
    agent: ScreeningAgent = _state["agent"]
    per_example: list[dict[str, Any]] = []
    fp = fn = agreed = 0
    for example in body.examples:
        scorecard = await agent.screen(example.candidate, example.requisition)
        match = scorecard.qualified == example.expected_qualified
        if match:
            agreed += 1
        elif scorecard.qualified and not example.expected_qualified:
            fp += 1
        else:
            fn += 1
        per_example.append(
            {
                "candidate_first_name": example.candidate.first_name,
                "candidate_last_name": example.candidate.last_name,
                "expected": example.expected_qualified,
                "actual": scorecard.qualified,
                "pass_ratio": scorecard.pass_ratio,
                "match": match,
                "summary": scorecard.summary[:240],
            }
        )
    rate = agreed / len(body.examples)
    return CalibrationReport(
        total=len(body.examples),
        agreed=agreed,
        agreement_rate=round(rate, 4),
        target=body.target_agreement,
        passed_target=rate >= body.target_agreement,
        false_positives=fp,
        false_negatives=fn,
        per_example=per_example,
    )
