"""Opportunity staffing feasibility analyzer.

Capture team supplies a draft contract: required LCATs, headcount per
LCAT, period of performance, location. We produce:
- Risk score 0-100 (higher = riskier to commit)
- Talent supply estimate per LCAT (counts from candidate DB OR a
  manually-supplied lookup for offline operation)
- Recommended pre-positioning actions
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class LcatRequirement:
    lcat_code: str
    headcount: int
    clearance_required: str  # none | secret | top_secret | ts_sci
    polygraph_required: str | None = None
    location: str | None = None


@dataclass
class TalentEstimate:
    lcat_code: str
    addressable_pool: int
    available_now_pool: int
    in_pipeline: int


@dataclass
class FeasibilityScore:
    overall_risk: int          # 0-100, higher = riskier
    overall_status: str        # feasible | difficult | infeasible
    estimates: list[TalentEstimate]
    recommendations: list[str] = field(default_factory=list)
    summary: str = ""


CountFn = Callable[[str, str, str | None, str | None, bool], int]
"""Signature: (lcat_code, clearance, polygraph, location, available_now) -> count."""


def analyze(
    requirements: list[LcatRequirement],
    *,
    count_fn: CountFn | None = None,
) -> FeasibilityScore:
    estimates: list[TalentEstimate] = []
    recommendations: list[str] = []
    risk_score = 0
    risk_total = 0

    counter = count_fn or _zero_count
    for req in requirements:
        addressable = counter(
            req.lcat_code, req.clearance_required, req.polygraph_required, req.location, False,
        )
        available_now = counter(
            req.lcat_code, req.clearance_required, req.polygraph_required, req.location, True,
        )
        in_pipeline = max(0, addressable - available_now)
        estimates.append(
            TalentEstimate(
                lcat_code=req.lcat_code,
                addressable_pool=addressable,
                available_now_pool=available_now,
                in_pipeline=in_pipeline,
            )
        )
        ratio = available_now / max(req.headcount, 1)
        if available_now == 0:
            risk = 100
            recommendations.append(
                f"{req.lcat_code}: zero available — pre-position via LOI sourcing immediately."
            )
        elif ratio < 1.0:
            risk = int(100 * (1 - ratio))
            recommendations.append(
                f"{req.lcat_code}: {available_now} available vs {req.headcount} required — "
                "engage adjacent talent + ramp pre-award outreach."
            )
        elif ratio < 2.0:
            risk = 30
        else:
            risk = 10
        risk_score += risk * req.headcount
        risk_total += req.headcount

    overall_risk = risk_score // max(risk_total, 1)
    if overall_risk >= 75:
        status = "infeasible"
    elif overall_risk >= 40:
        status = "difficult"
    else:
        status = "feasible"
    summary = (
        f"Overall risk {overall_risk}/100 ({status}). "
        f"{len(estimates)} LCATs analysed; {sum(e.available_now_pool for e in estimates)} "
        f"candidates available now across all roles."
    )
    return FeasibilityScore(
        overall_risk=overall_risk,
        overall_status=status,
        estimates=estimates,
        recommendations=recommendations,
        summary=summary,
    )


def _zero_count(*args, **kwargs) -> int:
    return 0
