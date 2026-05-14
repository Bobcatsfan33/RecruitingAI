"""Interaction event envelope shipped to ClickHouse."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(str, Enum):
    OUTREACH_SENT = "outreach_sent"
    OUTREACH_OPENED = "outreach_opened"
    OUTREACH_CLICKED = "outreach_clicked"
    OUTREACH_REPLIED = "outreach_replied"
    SCREEN_STARTED = "screen_started"
    SCREEN_COMPLETED = "screen_completed"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    SUBMISSION_SENT = "submission_sent"
    FEEDBACK_RECEIVED = "feedback_received"
    OFFER_EXTENDED = "offer_extended"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    CANDIDATE_STARTED = "candidate_started"
    CANDIDATE_FALLOFF = "candidate_falloff"
    PLACEMENT_90DAY = "placement_90day"
    REFERRAL_RECEIVED = "referral_received"
    PROFILE_UPDATED = "profile_updated"
    ENRICHMENT_COMPLETED = "enrichment_completed"


class AgentType(str, Enum):
    SOURCER = "sourcer"
    SCREENING = "screening"
    OUTREACH = "outreach"
    INTERVIEW = "interview"
    PIPELINE_MANAGER = "pipeline_manager"
    COMPLIANCE = "compliance"
    BENCH_MANAGEMENT = "bench_management"
    CLIENT_ADVISORY = "client_advisory"
    CLOSE_PROTECTION = "close_protection"
    CLIENT_DEVELOPMENT = "client_development"
    SYSTEM = "system"


class Channel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    PHONE = "phone"
    SMS = "sms"
    VOICE_AI = "voice_ai"
    CHAT = "chat"
    PORTAL = "portal"


class Outcome(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    PENDING = "pending"


class InteractionEvent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: EventType
    candidate_id: UUID
    requisition_id: UUID | None = None
    client_id: UUID | None = None
    agent_type: AgentType = AgentType.SYSTEM
    channel: Channel | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    outcome: Outcome | None = None
    cost_usd: float | None = None
    duration_seconds: int | None = None
