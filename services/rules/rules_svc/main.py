"""Rules service FastAPI app.

Routes
------
GET  /v1/health                 — readiness (also pings OPA)
GET  /v1/rules                  — list registered rules
POST /v1/rules/{name}           — evaluate one rule with body {"input": {...}}
POST /v1/rules/batch            — evaluate many rules with the same input
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from rules_svc.opa_client import OpaClient
from rules_svc.registry import REGISTRY

log = structlog.get_logger("rules")
logging.basicConfig(level="INFO")

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    _state["opa"] = OpaClient()
    log.info("rules_service_started", rules=list(REGISTRY))
    yield
    await _state["opa"].aclose()


app = FastAPI(title="WFI Rules", version="0.1.0", lifespan=lifespan)


class EvaluateRequest(BaseModel):
    input: dict[str, Any]


class BatchRequest(BaseModel):
    rules: list[str]
    input: dict[str, Any]


@app.get("/v1/health")
async def health() -> dict[str, Any]:
    opa: OpaClient = _state["opa"]
    return {"status": "ok", "opa_reachable": await opa.health(), "rules": len(REGISTRY)}


@app.get("/v1/rules")
async def list_rules() -> list[dict[str, Any]]:
    return [
        {"name": spec.name, "package": spec.package, "description": spec.description}
        for spec in REGISTRY.values()
    ]


@app.post("/v1/rules/{name}")
async def evaluate(name: str, body: EvaluateRequest) -> dict[str, Any]:
    spec = REGISTRY.get(name)
    if not spec:
        raise HTTPException(404, f"unknown rule {name}")
    opa: OpaClient = _state["opa"]
    result = await opa.evaluate(spec.package, spec.rule, body.input)
    if not result:
        # OPA returned undefined — treat as a default-deny allow + flag.
        return {"rule": name, "verdict": "undefined", "reasoning": "OPA returned no result", "details": {}}
    result.setdefault("rule", name)
    return result


@app.post("/v1/rules/batch")
async def evaluate_batch(body: BatchRequest) -> dict[str, list[dict[str, Any]]]:
    opa: OpaClient = _state["opa"]
    results: list[dict[str, Any]] = []
    for name in body.rules:
        spec = REGISTRY.get(name)
        if not spec:
            results.append(
                {"rule": name, "verdict": "unknown_rule", "reasoning": "rule not in registry", "details": {}}
            )
            continue
        try:
            result = await opa.evaluate(spec.package, spec.rule, body.input)
        except RuntimeError as exc:
            results.append({"rule": name, "verdict": "error", "reasoning": str(exc), "details": {}})
            continue
        if not result:
            results.append({"rule": name, "verdict": "undefined", "reasoning": "OPA returned no result", "details": {}})
            continue
        result.setdefault("rule", name)
        results.append(result)
    return {"results": results}
