"""Candidate schema (mirrors `candidates` SQL table)."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CandidateSource(str, Enum):
    LINKEDIN = "linkedin"
    CLEARANCE_JOBS = "clearancejobs"
    REFERRAL = "referral"
    INBOUND = "inbound"
    MANUAL = "manual"


class CandidateStatus(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"
    DO_NOT_CONTACT = "do_not_contact"
    PLACED = "placed"
    BENCHED = "benched"


class Citizenship(str, Enum):
    US_CITIZEN = "us_citizen"
    PERMANENT_RESIDENT = "permanent_resident"
    VISA_H1B = "visa_h1b"
    VISA_OTHER = "visa_other"
    UNKNOWN = "unknown"


class ClearanceType(str, Enum):
    NONE = "none"
    PUBLIC_TRUST = "public_trust"
    SECRET = "secret"
    TOP_SECRET = "top_secret"
    TS_SCI = "ts_sci"


class PolygraphType(str, Enum):
    NONE = "none"
    CI = "ci"
    FULL_SCOPE = "full_scope"
    LIFESTYLE = "lifestyle"


class ClearanceStatus(str, Enum):
    ACTIVE = "active"
    INTERIM = "interim"
    EXPIRED = "expired"
    IN_PROCESS = "in_process"


class CareerArc(str, Enum):
    ASCENDING = "ascending"
    LATERAL = "lateral"
    DECLINING = "declining"
    PIVOTING = "pivoting"


class CompTrajectory(str, Enum):
    GROWING = "growing"
    FLAT = "flat"
    DECLINING = "declining"


class SalesMotion(str, Enum):
    ENTERPRISE = "enterprise"
    MID_MARKET = "mid_market"
    SMB_VELOCITY = "smb_velocity"
    PLG = "plg"
    CHANNEL = "channel"


class SeOrientation(str, Enum):
    PRE_SALES = "pre_sales"
    POST_SALES = "post_sales"
    HYBRID = "hybrid"


class PreferredChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    PHONE = "phone"
    TEXT = "text"


class AvailabilityWindow(str, Enum):
    IMMEDIATELY = "immediately"
    TWO_WEEKS = "two_weeks"
    THIRTY_DAYS = "thirty_days"
    NOT_LOOKING = "not_looking"


class CareerHistoryEntry(BaseModel):
    company: str
    title: str
    start_date: date | None = None
    end_date: date | None = None
    company_tier: str | None = None  # platform | established | growth | early
    motion_type: SalesMotion | None = None
    quota_level: float | None = None
    territory: str | None = None
    notes: str | None = None


class CompensationEntry(BaseModel):
    role_id: str | None = None
    base: float | None = None
    ote: float | None = None
    variable_structure: str | None = None
    accelerators: bool | None = None
    equity: str | None = None
    signing_bonus: float | None = None
    w2_verified: bool = False
    year: int | None = None


class EngagementSignals(BaseModel):
    last_contact_date: datetime | None = None
    last_response_date: datetime | None = None
    preferred_channel: PreferredChannel | None = None
    response_rate_email: float | None = Field(default=None, ge=0, le=1)
    response_rate_linkedin: float | None = Field(default=None, ge=0, le=1)
    response_rate_phone: float | None = Field(default=None, ge=0, le=1)
    approachability_score: int | None = Field(default=None, ge=0, le=100)
    counteroffer_risk_score: int | None = Field(default=None, ge=0, le=100)
    availability_window: AvailabilityWindow | None = None
    referral_connections: list[UUID] = Field(default_factory=list)


class Candidate(BaseModel):
    """Canonical candidate record."""

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source: CandidateSource
    status: CandidateStatus = CandidateStatus.ACTIVE

    # Identity
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    location_city: str | None = None
    location_state: str | None = None
    location_metro: str | None = None
    willing_to_relocate: bool = False
    citizenship: Citizenship = Citizenship.UNKNOWN

    # Career + comp
    career_history: list[CareerHistoryEntry] = Field(default_factory=list)
    career_arc_classification: CareerArc | None = None
    compensation_history: list[CompensationEntry] = Field(default_factory=list)
    comp_trajectory: CompTrajectory | None = None

    # Sales motion
    primary_motion: SalesMotion | None = None
    secondary_motion: SalesMotion | None = None
    deal_cycle_min_days: int | None = Field(default=None, ge=0)
    deal_cycle_max_days: int | None = Field(default=None, ge=0)
    deal_cycle_avg_days: int | None = Field(default=None, ge=0)
    avg_acv: float | None = Field(default=None, ge=0)
    max_acv: float | None = Field(default=None, ge=0)
    methodology_experience: list[str] = Field(default_factory=list)

    # SE depth
    se_domains: list[dict[str, Any]] = Field(default_factory=list)
    se_vendor_specific: list[dict[str, Any]] = Field(default_factory=list)
    se_orientation: SeOrientation | None = None
    se_demo_skill_rating: int | None = Field(default=None, ge=1, le=5)

    # Clearance
    clearance_type: ClearanceType = ClearanceType.NONE
    polygraph: PolygraphType = PolygraphType.NONE
    investigation_date: date | None = None
    adjudication_date: date | None = None
    clearance_status: ClearanceStatus | None = None
    read_on_history: list[dict[str, Any]] = Field(default_factory=list)
    facility_clearance_affiliations: list[dict[str, Any]] = Field(default_factory=list)
    itar_ear_eligible: bool = False
    sap_sar_access: list[dict[str, Any]] = Field(default_factory=list)
    deployability_score: int | None = Field(default=None, ge=0, le=100)

    # Engagement signals
    engagement: EngagementSignals = Field(default_factory=EngagementSignals)

    # Metadata
    data_freshness_score: int = Field(default=100, ge=0, le=100)
    last_enrichment_date: datetime | None = None
    profile_completeness_score: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def _strip_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip().lower()
        return cleaned or None

    def has_contact(self) -> bool:
        """True if at least one contact channel is populated."""
        return any([self.email, self.phone, self.linkedin_url])
