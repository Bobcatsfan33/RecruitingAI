"""Co-employment risk monitoring helpers.

The OPA `co_employment_risk` rule is the source of truth; this module is a
local helper that ranks bench rows by their inputs WITHOUT a network round
trip, so dashboards can render the bench bench under load. For a final
verdict we still call the rules service.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CoEmploymentInputs:
    candidate_id: str
    tenure_months: int
    hours_per_week: int
    supervision_model: str  # direct_client_management | vendor_managed | self_directed


@dataclass
class CoEmploymentSummary:
    candidate_id: str
    risk_score: int
    risk_band: str       # low | medium | high
    triggered_thresholds: list[str]


def summarise(inputs: CoEmploymentInputs) -> CoEmploymentSummary:
    triggered: list[str] = []
    score = 0
    if inputs.tenure_months > 18:
        score += 30
        triggered.append("tenure>18m")
    if inputs.tenure_months > 24:
        score += 20
        triggered.append("tenure>24m")
    if inputs.hours_per_week >= 30:
        score += 15
        triggered.append("hours>=30 (ACA)")
    if inputs.hours_per_week >= 40:
        score += 10
        triggered.append("hours>=40")
    if inputs.supervision_model == "direct_client_management":
        score += 25
        triggered.append("direct_client_management")
    if score >= 50:
        band = "high"
    elif score >= 30:
        band = "medium"
    else:
        band = "low"
    return CoEmploymentSummary(
        candidate_id=inputs.candidate_id,
        risk_score=score,
        risk_band=band,
        triggered_thresholds=triggered,
    )
