"""Outcomes FastAPI surface."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from outcomes_svc.features import (
    OFFER_ACCEPTANCE_FEATURES,
    PLACEMENT_FEATURES,
)
from outcomes_svc.models import (
    Predictor,
    TrainResult,
    load,
    save,
    train_offer_acceptance_model,
    train_placement_model,
)
from outcomes_svc.retention import (
    RetentionSurvey,
    RetentionWindow,
    label_survey,
    schedule_surveys,
    score_satisfaction,
)
from outcomes_svc.synthetic import (
    synthesize_offer_acceptance_dataset,
    synthesize_placement_dataset,
)

log = structlog.get_logger("outcomes")


_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    # On startup, try to load both models from disk; if missing, train on
    # the synthetic dataset so the service answers predict requests
    # immediately. Real-world data replaces synthetic via /v1/outcomes/retrain.
    for name, dataset_fn, trainer in (
        ("placement_success", synthesize_placement_dataset, train_placement_model),
        ("offer_acceptance", synthesize_offer_acceptance_dataset, train_offer_acceptance_model),
    ):
        try:
            _state[name] = load(name)
            log.info("model_loaded_from_disk", name=name)
        except FileNotFoundError:
            predictor, result = trainer(dataset_fn())
            save(predictor, name=name)
            _state[name] = predictor
            _state[f"{name}_train_result"] = result
            log.info("model_trained_synthetic", name=name, test_auc=result.test_auc)
    yield


app = FastAPI(title="WFI Outcomes", version="0.1.0", lifespan=lifespan)


class PredictRequest(BaseModel):
    features: dict[str, float]


class RetrainRequest(BaseModel):
    feature_set: str  # placement_success | offer_acceptance
    n: int = 1500
    seed: int = 0


class ScheduleSurveysRequest(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    placement_date: datetime


class ScoreSurveyRequest(BaseModel):
    candidate_id: UUID
    requisition_id: UUID
    window: RetentionWindow
    sent_at: datetime
    candidate_response: dict[str, Any] | None = None
    hiring_manager_response: dict[str, Any] | None = None


@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    return {
        name: {
            "feature_set": getattr(_state.get(name), "feature_set", None),
            "feature_count": len(getattr(_state.get(name), "feature_names", []) or []),
        }
        for name in ("placement_success", "offer_acceptance")
    }


@app.post("/v1/predict/{model_name}")
async def predict(model_name: str, body: PredictRequest) -> dict[str, Any]:
    predictor: Predictor | None = _state.get(model_name)
    if predictor is None:
        raise HTTPException(404, f"model {model_name} not loaded")
    proba = predictor.predict_proba(body.features)
    explanation = predictor.explain(body.features)
    return {
        "model": model_name,
        "probability_positive": round(proba, 4),
        "feature_contributions": explanation,
    }


@app.post("/v1/outcomes/retrain")
async def retrain(req: RetrainRequest) -> TrainResult:
    if req.feature_set == "placement_success":
        rows = synthesize_placement_dataset(seed=req.seed, n=req.n)
        predictor, result = train_placement_model(rows)
    elif req.feature_set == "offer_acceptance":
        rows = synthesize_offer_acceptance_dataset(seed=req.seed, n=req.n)
        predictor, result = train_offer_acceptance_model(rows)
    else:
        raise HTTPException(400, "unknown feature set")
    save(predictor, name=req.feature_set)
    _state[req.feature_set] = predictor
    return result


@app.post("/v1/retention/schedule")
async def retention_schedule(req: ScheduleSurveysRequest) -> list[dict[str, Any]]:
    surveys = schedule_surveys(
        candidate_id=req.candidate_id,
        requisition_id=req.requisition_id,
        placement_date=req.placement_date,
    )
    return [
        {
            "id": str(s.id),
            "candidate_id": str(s.candidate_id),
            "requisition_id": str(s.requisition_id),
            "window": s.window,
            "sent_at": s.sent_at.isoformat(),
        }
        for s in surveys
    ]


@app.post("/v1/retention/score")
async def retention_score(req: ScoreSurveyRequest) -> dict[str, Any]:
    survey = RetentionSurvey(
        id=UUID(int=0),
        candidate_id=req.candidate_id,
        requisition_id=req.requisition_id,
        window=req.window,
        sent_at=req.sent_at,
        candidate_response=req.candidate_response,
        hiring_manager_response=req.hiring_manager_response,
    )
    score = score_satisfaction(survey)
    return {
        "candidate_id": str(score.candidate_id),
        "requisition_id": str(score.requisition_id),
        "candidate_score": score.candidate_score,
        "hiring_manager_score": score.hiring_manager_score,
        "average": score.average,
    }
