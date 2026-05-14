"""Scorecard schema produced by the screening + interview agents."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Recommendation(str, Enum):
    STRONG_YES = "strong_yes"
    YES = "yes"
    MAYBE = "maybe"
    NO = "no"
    STRONG_NO = "strong_no"


class EscalationFlag(str, Enum):
    VP_PLUS = "vp_plus"
    HIGH_COMP = "high_comp_350k_plus"
    ACTIVE_NON_COMPETE = "active_non_compete"
    MIXED_SIGNALS = "mixed_signals"
    HIGH_VALUE_INTERVIEW = "high_value_interview"
    OWNERSHIP_BLOCKED = "ownership_blocked"
    COMPLIANCE_REVIEW = "compliance_review"


class DimensionScore(BaseModel):
    dimension: str
    score: float = Field(ge=0.0, le=5.0)
    reasoning: str
    evidence_quotes: list[str] = Field(default_factory=list)
    weight: float = 1.0


class Scorecard(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    candidate_id: UUID
    requisition_id: UUID
    agent: str
    model_used: str

    # Headline result
    qualified: bool
    pass_ratio: float = Field(ge=0.0, le=1.0)
    recommendation: Recommendation
    confidence: float = Field(ge=0.0, le=1.0)

    # Per-criterion + per-dimension detail
    criterion_results: list[dict[str, Any]] = Field(default_factory=list)
    dimensional_scores: list[DimensionScore] = Field(default_factory=list)

    # Risk + escalation
    risk_flags: list[str] = Field(default_factory=list)
    escalations: list[EscalationFlag] = Field(default_factory=list)

    # Free-form rationale + redacted input summary
    summary: str
    input_summary: str = ""
    cost_usd: float | None = None
    latency_ms: int | None = None
