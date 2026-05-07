"""Pipeline state machine — Intake -> Sourcing -> Screening -> Outreach ->
Interview -> Submission -> Offer -> Onboarding."""

from __future__ import annotations

from enum import Enum


class Stage(str, Enum):
    INTAKE = "intake"
    SOURCING = "sourcing"
    SCREENING = "screening"
    OUTREACH = "outreach"
    INTERVIEW = "interview"
    SUBMISSION = "submission"
    OFFER = "offer"
    ONBOARDING = "onboarding"
    PLACED = "placed"
    DECLINED = "declined"
    FALLOFF = "falloff"


# Allowed forward transitions. Backward transitions are explicit (e.g.
# moving back from offer -> interview when client requests another round).
TRANSITIONS: dict[Stage, set[Stage]] = {
    Stage.INTAKE: {Stage.SOURCING, Stage.SCREENING, Stage.DECLINED},
    Stage.SOURCING: {Stage.SCREENING, Stage.DECLINED},
    Stage.SCREENING: {Stage.OUTREACH, Stage.DECLINED, Stage.SUBMISSION},
    Stage.OUTREACH: {Stage.INTERVIEW, Stage.SCREENING, Stage.DECLINED},
    Stage.INTERVIEW: {Stage.SUBMISSION, Stage.OUTREACH, Stage.DECLINED, Stage.OFFER},
    Stage.SUBMISSION: {Stage.OFFER, Stage.INTERVIEW, Stage.DECLINED},
    Stage.OFFER: {Stage.ONBOARDING, Stage.DECLINED, Stage.FALLOFF},
    Stage.ONBOARDING: {Stage.PLACED, Stage.FALLOFF},
    Stage.PLACED: set(),
    Stage.DECLINED: set(),
    Stage.FALLOFF: {Stage.SCREENING, Stage.SUBMISSION},  # silver-medalist re-entry
}


def can_transition(from_stage: Stage, to_stage: Stage) -> bool:
    return to_stage in TRANSITIONS.get(from_stage, set())


PENULTIMATE_STAGE = Stage.SUBMISSION  # where silver medalists are held
