"""Capture FastAPI surface."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI
from pydantic import BaseModel

from capture_svc.comp_estimator import CompEstimate, estimate
from capture_svc.feasibility import (
    FeasibilityScore,
    LcatRequirement,
    analyze,
)
from capture_svc.heatmap import CandidateFacet, HeatmapCell, build, summarise_by_clearance
from capture_svc.loi import Loi, draft_loi, package

log = structlog.get_logger("capture")


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    _state["lois"] = {}
    log.info("capture_service_started")
    yield


app = FastAPI(title="WFI Capture Intelligence", version="0.1.0", lifespan=lifespan)


class FeasibilityRequest(BaseModel):
    requirements: list[LcatRequirement]


class HeatmapRequest(BaseModel):
    facets: list[CandidateFacet]


class CompEstimateRequest(BaseModel):
    lcat_level: str
    location: str = "DC Metro"
    clearance: str = "secret"
    polygraph: str = "none"
    target_margin: float = 0.30


class LoiDraftRequest(BaseModel):
    candidate_id: UUID
    opportunity_name: str
    contract_vehicle: str
    lcat_code: str
    period_of_performance_start: date
    period_of_performance_end: date
    proposed_salary: int | None = None
    proposed_bill_rate: float | None = None
    notes: str = ""


class LoiPackageRequest(BaseModel):
    opportunity_name: str
    contract_vehicle: str
    loi_ids: list[UUID]


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/capture/feasibility")
async def feasibility(req: FeasibilityRequest) -> FeasibilityScore:
    return analyze(req.requirements)


@app.post("/v1/capture/heatmap")
async def heatmap(req: HeatmapRequest) -> dict[str, Any]:
    cells: list[HeatmapCell] = build(req.facets)
    return {
        "cells": [c.__dict__ for c in cells],
        "by_clearance": summarise_by_clearance(cells),
        "total_candidates": sum(c.count for c in cells),
    }


@app.post("/v1/capture/comp/estimate")
async def comp_estimate(req: CompEstimateRequest) -> CompEstimate:
    return estimate(
        lcat_level=req.lcat_level,
        location=req.location,
        clearance=req.clearance,
        polygraph=req.polygraph,
        target_margin=req.target_margin,
    )


@app.post("/v1/capture/loi/draft")
async def loi_draft(req: LoiDraftRequest) -> Loi:
    loi = draft_loi(**req.model_dump())
    _state["lois"][loi.id] = loi
    return loi


@app.post("/v1/capture/loi/package")
async def loi_package(req: LoiPackageRequest) -> dict[str, Any]:
    lois: list[Loi] = [
        _state["lois"][lid]
        for lid in req.loi_ids
        if lid in _state["lois"]
    ]
    pkg = package(req.opportunity_name, req.contract_vehicle, lois)
    return {
        "opportunity_name": pkg.opportunity_name,
        "contract_vehicle": pkg.contract_vehicle,
        "submitted_at": pkg.submitted_at.isoformat(),
        "loi_count": len(pkg.lois),
        "acceptance_rate": pkg.acceptance_rate(),
        "lois": [loi.__dict__ for loi in pkg.lois],
    }
