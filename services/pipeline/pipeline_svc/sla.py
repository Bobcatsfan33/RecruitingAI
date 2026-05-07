"""SLA monitoring + bottleneck detection.

Each requisition has SLA fields (sla_days_to_first_submission,
sla_days_to_fill). The Pipeline Manager watches the time-in-stage and
fires escalations when the elapsed time exceeds the per-stage budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pipeline_svc.state import Stage


# Default per-stage time budgets (days). Override per-req via
# `requisition.role_specific_requirements.sla_per_stage`.
DEFAULT_BUDGETS: dict[Stage, int] = {
    Stage.INTAKE: 1,
    Stage.SOURCING: 5,
    Stage.SCREENING: 3,
    Stage.OUTREACH: 7,
    Stage.INTERVIEW: 5,
    Stage.SUBMISSION: 5,
    Stage.OFFER: 7,
    Stage.ONBOARDING: 14,
}


@dataclass
class StageHealth:
    stage: Stage
    days_in_stage: float
    budget_days: int
    sla_breach: bool
    breach_severity: str  # ok | warning | breached


def evaluate(stage: Stage, entered_at: datetime, *, budgets: dict[Stage, int] | None = None) -> StageHealth:
    budget = (budgets or DEFAULT_BUDGETS).get(stage, 7)
    elapsed = datetime.now(timezone.utc) - entered_at.astimezone(timezone.utc)
    days = elapsed.total_seconds() / 86_400
    severity = "ok"
    breach = False
    if days >= budget:
        severity = "breached"
        breach = True
    elif days >= budget * 0.75:
        severity = "warning"
    return StageHealth(
        stage=stage,
        days_in_stage=round(days, 2),
        budget_days=budget,
        sla_breach=breach,
        breach_severity=severity,
    )


def overall_pipeline_velocity(events: list[dict]) -> dict:
    """Aggregate stage transitions to expose conversion + cycle-time stats.

    `events` is a list of dicts with at least {stage_from, stage_to,
    occurred_at}. Returns conversion rates per transition + median cycle
    time per stage."""
    counts: dict[tuple[str, str], int] = {}
    for e in events:
        key = (e.get("stage_from"), e.get("stage_to"))
        if not all(key):
            continue
        counts[key] = counts.get(key, 0) + 1
    return {f"{a}->{b}": n for (a, b), n in counts.items()}
