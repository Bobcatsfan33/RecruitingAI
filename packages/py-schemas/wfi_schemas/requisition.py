"""Requisition + employer-defined rubric schema."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wfi_schemas.candidate import ClearanceType, PolygraphType, SalesMotion


class ReqType(str, Enum):
    PRECISION = "precision"
    VELOCITY = "velocity"
    PRE_AWARD = "pre_award"
    CONTINGENT = "contingent"
    DIRECT_HIRE = "direct_hire"


class ReqStatus(str, Enum):
    INTAKE = "intake"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    FILLED = "filled"
    CANCELLED = "cancelled"


class ReqUrgency(str, Enum):
    CRITICAL_48H = "critical_48h"
    STANDARD_2WK = "standard_2wk"
    PIPELINE_30D = "pipeline_30d"
    PRE_AWARD_SPECULATIVE = "pre_award_speculative"


class ReqConvictionTier(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


class ReqExclusivity(str, Enum):
    EXCLUSIVE = "exclusive"
    NON_EXCLUSIVE = "non_exclusive"
    PREFERRED = "preferred"


class CompType(str, Enum):
    SALARY = "salary"
    HOURLY = "hourly"
    CONTRACT = "contract"


class RubricCriterion(BaseModel):
    """One employer-defined gate.

    The screening agent (Sprint 3) treats a candidate as passing when at
    least 85% of the active criteria for a requisition evaluate True. The
    employer owns the rubric; the agent owns the evaluation.
    """

    key: str
    description: str
    weight: float = Field(default=1.0, ge=0.0, le=10.0)
    severity: str = Field(default="must_have")  # must_have | nice_to_have | informational
    # Predicates the agent will evaluate:
    #   - "field_eq:foo=bar"
    #   - "field_gte:years_experience>=7"
    #   - "field_in:primary_motion in [enterprise, mid_market]"
    #   - "llm:prompt-key" — defer to LLM rubric block (handled by screening service)
    predicate: str
    pass_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class EmployerRubric(BaseModel):
    """Employer-defined pass criteria — the calibration replacement for the
    "85% recruiter agreement" metric in the blueprint.
    """

    pass_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    criteria: list[RubricCriterion] = Field(default_factory=list)
    notes: str | None = None

    def must_have_count(self) -> int:
        return sum(1 for c in self.criteria if c.severity == "must_have")


class Requisition(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    id: UUID | None = None
    client_id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    status: ReqStatus = ReqStatus.INTAKE

    # Classification
    req_type: ReqType
    urgency: ReqUrgency = ReqUrgency.STANDARD_2WK
    conviction_tier: ReqConvictionTier = ReqConvictionTier.MODERATE
    exclusivity: ReqExclusivity = ReqExclusivity.NON_EXCLUSIVE

    # Role
    title: str = Field(min_length=1)
    level: str | None = None
    department: str | None = None
    location_requirements: dict[str, Any] = Field(default_factory=dict)
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    years_experience_min: int | None = Field(default=None, ge=0)
    years_experience_max: int | None = Field(default=None, ge=0)
    education_requirement: str | None = None
    role_specific_requirements: dict[str, Any] = Field(default_factory=dict)

    # Sales-specific
    motion_type_required: SalesMotion | None = None
    quota_range_min: float | None = None
    quota_range_max: float | None = None
    vertical_experience_required: list[str] = Field(default_factory=list)
    stack_requirements: dict[str, Any] = Field(default_factory=dict)
    company_tier_preference: str | None = None

    # Clearance
    clearance_minimum: ClearanceType = ClearanceType.NONE
    polygraph_required: PolygraphType = PolygraphType.NONE
    contract_vehicle: str | None = None
    lcat_code: str | None = None
    lcat_definition: dict[str, Any] | None = None
    period_of_performance_start: date | None = None
    period_of_performance_end: date | None = None
    facility_clearance_required: bool = False

    # Compensation
    comp_type: CompType
    budget_min: float | None = None
    budget_max: float | None = None
    pay_rate_min: float | None = None
    pay_rate_max: float | None = None
    target_margin_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    conversion_fee_pct: float | None = Field(default=None, ge=0.0, le=1.0)
    market_alignment_score: int | None = Field(default=None, ge=0, le=100)

    # Pipeline metrics
    target_submissions: int = Field(default=5, ge=1)
    parallel_candidates_required: int = Field(default=3, ge=0)
    sla_days_to_first_submission: int | None = None
    sla_days_to_fill: int | None = None
    current_stage_counts: dict[str, int] = Field(default_factory=dict)

    # Competitive
    other_agencies_known: list[str] = Field(default_factory=list)
    competitive_pressure: str = "low"
    speed_vs_quality_weight: float = Field(default=0.5, ge=0.0, le=1.0)

    # Employer rubric (Sprint 3)
    employer_rubric: EmployerRubric = Field(default_factory=EmployerRubric)
