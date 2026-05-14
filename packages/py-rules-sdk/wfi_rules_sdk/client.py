"""HTTP client for the rules service."""

from __future__ import annotations

import os
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

Verdict = Literal[
    "feasible", "infeasible", "warning", "blocked", "allowed", "required",
    "expired", "valid", "approved", "rejected", "high_risk", "medium_risk",
    "low_risk", "clear", "risk", "likely_clear", "velocity", "precision",
    "balanced", "difficult",
]


class RuleEvaluation(BaseModel):
    rule: str
    verdict: Verdict | str
    reasoning: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    suggestions: list[str] = Field(default_factory=list)


class RulesClient:
    def __init__(self, base_url: str, *, timeout: float = 5.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    @classmethod
    def from_env(cls) -> RulesClient:
        return cls(os.environ.get("RULES_SERVICE_URL", "http://localhost:8001"))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def evaluate(self, rule: str, inputs: dict[str, Any]) -> RuleEvaluation:
        response = await self._client.post(
            f"{self._base_url}/v1/rules/{rule}",
            json={"input": inputs},
        )
        response.raise_for_status()
        return RuleEvaluation(**response.json())

    async def evaluate_many(
        self,
        rules: list[str],
        inputs: dict[str, Any],
    ) -> list[RuleEvaluation]:
        response = await self._client.post(
            f"{self._base_url}/v1/rules/batch",
            json={"rules": rules, "input": inputs},
        )
        response.raise_for_status()
        return [RuleEvaluation(**item) for item in response.json()["results"]]
