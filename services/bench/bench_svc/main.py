"""Bench + compliance FastAPI surface."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI
from pydantic import BaseModel

from bench_svc.coemployment import CoEmploymentInputs, summarise
from bench_svc.compliance_adapters import (
    BackgroundCheckResult,
    ClearanceVerificationResult,
    EVerifyResult,
    select_background,
    select_diss,
    select_everify,
)
from bench_svc.conversion import compute, utilisation_rate
from bench_svc.lifecycle import (
    BenchAlert,
    ContractorRecord,
    evaluate_bench,
    evaluate_contractor,
)

log = structlog.get_logger("bench")


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    _state["bgc"] = select_background()
    _state["diss"] = select_diss()
    _state["everify"] = select_everify()
    log.info("bench_service_started")
    yield


app = FastAPI(title="WFI Bench + Compliance", version="0.1.0", lifespan=lifespan)


class EvaluateBenchRequest(BaseModel):
    records: list[ContractorRecord]
    today: date | None = None


class CoEmploymentRequest(BaseModel):
    inputs: CoEmploymentInputs


class ConversionRequest(BaseModel):
    hours_worked: int
    bill_rate: float
    first_year_salary: int
    conversion_pct: float = 0.20
    credit_per_hour: float = 0.0
    waiver_threshold_hours: int = 1000


class UtilisationRequest(BaseModel):
    bench_hours: int
    billable_hours: int


class BackgroundCheckRequest(BaseModel):
    candidate_email: str
    package: str = "standard"


class DissVerifyRequest(BaseModel):
    candidate_id: UUID


class EVerifyRequest(BaseModel):
    candidate_email: str
    document_type: str
    document_number: str


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/bench/evaluate")
async def bench_evaluate(req: EvaluateBenchRequest) -> list[BenchAlert]:
    return evaluate_bench(req.records, today=req.today)


@app.post("/v1/bench/contractor")
async def bench_contractor(record: ContractorRecord) -> list[BenchAlert]:
    return evaluate_contractor(record)


@app.post("/v1/bench/coemployment")
async def bench_coemployment(req: CoEmploymentRequest) -> dict[str, Any]:
    return summarise(req.inputs).__dict__


@app.post("/v1/bench/conversion")
async def bench_conversion(req: ConversionRequest) -> dict[str, Any]:
    return compute(**req.model_dump()).__dict__


@app.post("/v1/bench/utilisation")
async def bench_utilisation(req: UtilisationRequest) -> dict[str, float]:
    return {"utilisation": utilisation_rate(
        bench_hours=req.bench_hours, billable_hours=req.billable_hours,
    )}


@app.post("/v1/compliance/background/initiate")
async def compliance_background_initiate(req: BackgroundCheckRequest) -> BackgroundCheckResult:
    return await _state["bgc"].initiate(
        candidate_email=req.candidate_email, package=req.package,
    )


@app.get("/v1/compliance/background/{case_id}")
async def compliance_background_status(case_id: str) -> BackgroundCheckResult:
    return await _state["bgc"].fetch_status(case_id)


@app.post("/v1/compliance/diss")
async def compliance_diss(req: DissVerifyRequest) -> ClearanceVerificationResult:
    return await _state["diss"].verify(candidate_id=str(req.candidate_id))


@app.post("/v1/compliance/everify")
async def compliance_everify(req: EVerifyRequest) -> EVerifyResult:
    return await _state["everify"].submit(
        candidate_email=req.candidate_email,
        document_type=req.document_type,
        document_number=req.document_number,
    )
