"""Competitive agency intelligence.

For each requisition, we score 'competitive pressure' as a 0-100 number
combining:
- candidates self-reporting outreach from other agencies (weight 50)
- agency job postings mirroring our active req (weight 30)
- candidate LinkedIn activity from known agency profiles (weight 20)

Inputs are caller-supplied; the dashboard wires this into the Sourcer +
Pipeline Manager so the platform can recommend "speed up timeline,
adjust markup, increase candidate touch frequency".
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompetitiveSignals:
    requisition_id: str
    candidates_reporting_competing_outreach: int = 0
    candidates_evaluated: int = 1
    competing_agency_postings_count: int = 0
    candidates_with_competing_li_activity: int = 0


@dataclass
class CompetitiveAssessment:
    requisition_id: str
    pressure_score: int  # 0-100
    band: str            # low | medium | high
    recommended_actions: list[str] = field(default_factory=list)
    components: dict[str, float] = field(default_factory=dict)


def evaluate(signals: CompetitiveSignals) -> CompetitiveAssessment:
    outreach_ratio = (
        signals.candidates_reporting_competing_outreach
        / max(signals.candidates_evaluated, 1)
    )
    li_activity_ratio = (
        signals.candidates_with_competing_li_activity
        / max(signals.candidates_evaluated, 1)
    )
    posting_factor = min(1.0, signals.competing_agency_postings_count / 5.0)

    score = int(round(
        50 * outreach_ratio + 20 * li_activity_ratio + 30 * posting_factor
    ))
    score = max(0, min(100, score))

    if score >= 65:
        band = "high"
    elif score >= 35:
        band = "medium"
    else:
        band = "low"

    actions: list[str] = []
    if score >= 65:
        actions.append("compress timeline 30-50%")
        actions.append("escalate comp band toward 75th percentile")
        actions.append("increase candidate touch frequency to daily during close protection")
    elif score >= 35:
        actions.append("review comp competitiveness; share market data with client")
        actions.append("tighten outreach cadence")
    else:
        actions.append("standard cadence; re-evaluate weekly")

    return CompetitiveAssessment(
        requisition_id=signals.requisition_id,
        pressure_score=score,
        band=band,
        recommended_actions=actions,
        components={
            "competing_outreach_ratio": round(outreach_ratio, 4),
            "competing_li_ratio": round(li_activity_ratio, 4),
            "posting_factor": round(posting_factor, 4),
        },
    )
