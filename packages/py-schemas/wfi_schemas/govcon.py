"""GovCon contract-graph Pydantic models.

Mirror the SQL DDL in ``infrastructure/schema/init/01_govcon_*.sql``. Pure
types — importing this module triggers no I/O.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# --- Enums ----------------------------------------------------------------


class ContractStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ContractSource(str, Enum):
    SAM = "sam"
    FPDS = "fpds"
    USASPENDING = "usaspending"
    MANUAL = "manual"


class BaseOrOption(str, Enum):
    BASE = "base"
    OPTION = "option"


class RecompeteRisk(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    WATCH = "WATCH"
    STABLE = "STABLE"


class ClearanceLevel(str, Enum):
    NONE = "none"
    PUBLIC_TRUST = "public_trust"
    SECRET = "secret"
    TS = "ts"
    TS_SCI = "ts_sci"
    TS_SCI_POLY = "ts_sci_poly"


class PolyType(str, Enum):
    NONE = "none"
    CI = "ci"
    FULL_SCOPE = "full_scope"


class EducationLevel(str, Enum):
    HS = "HS"
    AA = "AA"
    BS = "BS"
    MS = "MS"
    PHD = "PhD"


class EmployeeStatus(str, Enum):
    ASSIGNED = "assigned"
    BENCH = "bench"
    PENDING_START = "pending_start"
    ROLLING_OFF = "rolling_off"


class AssignmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    PENDING = "pending"


class AdjudicationStatus(str, Enum):
    ACTIVE = "active"
    INTERIM = "interim"
    EXPIRED = "expired"
    REVOKED = "revoked"


class CertificationStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"


class RecompeteEventType(str, Enum):
    SOLICITATION = "solicitation"
    SOURCES_SOUGHT = "sources_sought"
    AWARD = "award"
    PROTEST = "protest"
    CANCELLATION = "cancellation"


class GapRiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    WATCH = "watch"
    LOW = "low"


class AlertTriggerType(str, Enum):
    RECOMPETE_APPROACHING = "recompete_approaching"
    SOLICITATION_DETECTED = "solicitation_detected"
    GAP_CREATED = "gap_created"
    GAP_CRITICAL = "gap_critical"
    BENCH_THRESHOLD = "bench_threshold"
    BENCH_COST_THRESHOLD = "bench_cost_threshold"
    CLEARANCE_EXPIRING = "clearance_expiring"
    ASSIGNMENT_ENDING = "assignment_ending"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertChannel(str, Enum):
    SLACK = "slack"
    EMAIL = "email"
    CALENDAR = "calendar"


class AlertStatus(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class SetAsideType(str, Enum):
    NONE = "none"
    EIGHT_A = "8a"
    SDVOSB = "SDVOSB"
    HUBZONE = "HUBZONE"
    WOSB = "WOSB"


# --- Core entities ----------------------------------------------------------


class Agency(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    code: str
    department: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Vendor(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    uei: str | None = None
    duns: str | None = None
    cage_code: str | None = None
    size_standard: str | None = None
    set_aside_type: SetAsideType | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Contract(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    piid: str
    title: str
    description: str | None = None
    naics_code: str | None = None
    contract_vehicle: str | None = None
    agency_id: UUID | None = None
    vendor_id: UUID | None = None
    pop_start: date | None = None
    pop_end: date | None = None
    current_value: Decimal | None = None
    potential_value: Decimal | None = None
    option_year: int | None = None
    base_or_option: BaseOrOption = BaseOrOption.BASE
    is_incumbent: bool = False
    recompete_risk: RecompeteRisk | None = None
    status: ContractStatus = ContractStatus.ACTIVE
    source: ContractSource = ContractSource.MANUAL
    raw_json: dict[str, Any] | None = None
    last_synced_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContractCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    piid: str
    title: str
    description: str | None = None
    naics_code: str | None = None
    contract_vehicle: str | None = None
    agency_id: UUID | None = None
    vendor_id: UUID | None = None
    pop_start: date | None = None
    pop_end: date | None = None
    current_value: Decimal | None = None
    potential_value: Decimal | None = None
    option_year: int | None = None
    base_or_option: BaseOrOption = BaseOrOption.BASE
    is_incumbent: bool = False
    recompete_risk: RecompeteRisk | None = None
    status: ContractStatus = ContractStatus.ACTIVE
    source: ContractSource = ContractSource.MANUAL
    raw_json: dict[str, Any] | None = None


class ContractUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: str | None = None
    description: str | None = None
    naics_code: str | None = None
    contract_vehicle: str | None = None
    agency_id: UUID | None = None
    vendor_id: UUID | None = None
    pop_start: date | None = None
    pop_end: date | None = None
    current_value: Decimal | None = None
    potential_value: Decimal | None = None
    option_year: int | None = None
    base_or_option: BaseOrOption | None = None
    is_incumbent: bool | None = None
    recompete_risk: RecompeteRisk | None = None
    status: ContractStatus | None = None


class Lcat(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    contract_id: UUID
    title: str
    labor_category: str | None = None
    min_education: EducationLevel | None = None
    min_experience_years: int = 0
    clearance_required: ClearanceLevel = ClearanceLevel.NONE
    location: str | None = None
    headcount: int = 1
    bill_rate_ceiling: Decimal | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LcatRequirement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    lcat_id: UUID
    requirement_type: str
    value: str
    is_mandatory: bool = True


class Employee(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    email: str
    clearance_level: ClearanceLevel = ClearanceLevel.NONE
    clearance_expiry: date | None = None
    poly_type: PolyType | None = None
    location: str | None = None
    education_level: EducationLevel | None = None
    years_experience: int | None = None
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    status: EmployeeStatus = EmployeeStatus.ASSIGNED
    bench_since: date | None = None
    monthly_cost: Decimal | None = None
    source_system: str | None = None
    external_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str
    email: str
    clearance_level: ClearanceLevel = ClearanceLevel.NONE
    clearance_expiry: date | None = None
    poly_type: PolyType | None = None
    location: str | None = None
    education_level: EducationLevel | None = None
    years_experience: int | None = None
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    status: EmployeeStatus = EmployeeStatus.ASSIGNED
    bench_since: date | None = None
    monthly_cost: Decimal | None = None
    source_system: str | None = None
    external_id: str | None = None


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    name: str | None = None
    email: str | None = None
    clearance_level: ClearanceLevel | None = None
    clearance_expiry: date | None = None
    poly_type: PolyType | None = None
    location: str | None = None
    education_level: EducationLevel | None = None
    years_experience: int | None = None
    skills: list[str] | None = None
    certifications: list[str] | None = None
    status: EmployeeStatus | None = None
    bench_since: date | None = None
    monthly_cost: Decimal | None = None


class Assignment(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    employee_id: UUID
    contract_id: UUID
    lcat_id: UUID | None = None
    start_date: date
    end_date: date | None = None
    status: AssignmentStatus = AssignmentStatus.ACTIVE
    bill_rate: Decimal | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Clearance(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    employee_id: UUID
    level: ClearanceLevel
    poly_type: PolyType | None = None
    investigation_date: date | None = None
    expiry_date: date | None = None
    adjudication_status: AdjudicationStatus = AdjudicationStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Certification(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    employee_id: UUID
    name: str
    issued_date: date | None = None
    expiry_date: date | None = None
    status: CertificationStatus = CertificationStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RecompeteEvent(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    contract_id: UUID
    event_type: RecompeteEventType
    detected_date: date
    sam_notice_id: str | None = None
    response_deadline: date | None = None
    details: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GapAnalysis(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    contract_id: UUID
    lcat_id: UUID
    required_count: int
    assigned_count: int
    bench_available: int
    gap_count: int
    risk_level: GapRiskLevel
    estimated_fill_days: int | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertRule(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    name: str
    trigger_type: AlertTriggerType
    threshold_value: int = 0
    severity: AlertSeverity = AlertSeverity.WARNING
    channel: AlertChannel = AlertChannel.SLACK
    recipients: list[str] = Field(default_factory=list)
    is_enabled: bool = True
    cooldown_hours: int = 24
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AlertHistory(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    alert_rule_id: UUID
    status: AlertStatus = AlertStatus.FIRING
    message: str
    context: dict[str, Any] = Field(default_factory=dict)
    fired_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
