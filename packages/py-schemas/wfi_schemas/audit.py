"""Immutable audit log entry."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ActionType(str, Enum):
    SCREEN_DECISION = "screen_decision"
    SCORE_ASSIGNED = "score_assigned"
    SUBMISSION_DECISION = "submission_decision"
    OUTREACH_SENT = "outreach_sent"
    INTERVIEW_EVALUATION = "interview_evaluation"
    OFFER_RECOMMENDATION = "offer_recommendation"
    ROUTING_DECISION = "routing_decision"
    ESCALATION_TRIGGERED = "escalation_triggered"
    COMPLIANCE_CHECK = "compliance_check"
    RULE_EVALUATION = "rule_evaluation"


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    log_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    action_type: ActionType
    candidate_id: UUID
    requisition_id: UUID | None = None
    agent_type: str
    model_used: str
    input_summary: str = ""
    decision: str
    reasoning: str = ""
    confidence_score: float = Field(ge=0.0, le=1.0)
    human_override: bool | None = None
    override_by: str | None = None
    override_reason: str | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
