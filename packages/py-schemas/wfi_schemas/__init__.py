"""Shared Pydantic schemas for the Workforce Intelligence platform.

These models mirror the SQL DDL and serve as the canonical wire format
between every service. Importing from `wfi_schemas` should never trigger
any I/O — pure types only.
"""

from wfi_schemas.candidate import (
    AvailabilityWindow,
    Candidate,
    CandidateSource,
    CandidateStatus,
    CareerArc,
    CareerHistoryEntry,
    Citizenship,
    ClearanceStatus,
    ClearanceType,
    CompensationEntry,
    CompTrajectory,
    EngagementSignals,
    PolygraphType,
    PreferredChannel,
    SalesMotion,
    SeOrientation,
)
from wfi_schemas.requisition import (
    CompType,
    EmployerRubric,
    Requisition,
    ReqConvictionTier,
    ReqExclusivity,
    ReqStatus,
    ReqType,
    ReqUrgency,
)
from wfi_schemas.events import (
    AgentType,
    Channel,
    EventType,
    InteractionEvent,
    Outcome,
)
from wfi_schemas.audit import ActionType, AuditLogEntry
from wfi_schemas.scorecard import (
    DimensionScore,
    EscalationFlag,
    Recommendation,
    Scorecard,
)

__all__ = [
    "ActionType",
    "AgentType",
    "AuditLogEntry",
    "AvailabilityWindow",
    "Candidate",
    "CandidateSource",
    "CandidateStatus",
    "CareerArc",
    "CareerHistoryEntry",
    "Channel",
    "Citizenship",
    "ClearanceStatus",
    "ClearanceType",
    "CompensationEntry",
    "CompTrajectory",
    "CompType",
    "DimensionScore",
    "EmployerRubric",
    "EngagementSignals",
    "EscalationFlag",
    "EventType",
    "InteractionEvent",
    "Outcome",
    "PolygraphType",
    "PreferredChannel",
    "Recommendation",
    "ReqConvictionTier",
    "ReqExclusivity",
    "ReqStatus",
    "ReqType",
    "ReqUrgency",
    "Requisition",
    "SalesMotion",
    "Scorecard",
    "SeOrientation",
]
