"""Stalled-pipeline diagnosis.

Given a requisition's pipeline event log, identify the stage that's the
bottleneck and suggest the most likely cause. Pure heuristic — produces
a structured diagnosis that the LLM-driven coaching layer (separate
function) can wrap into client-facing prose.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class StalledDiagnosis:
    bottleneck_stage: str | None
    bottleneck_days: float | None
    drop_off_stage: str | None
    drop_off_ratio: float | None
    likely_causes: list[str]
    recommendations: list[str]


def diagnose(events: list[dict]) -> StalledDiagnosis:
    if not events:
        return StalledDiagnosis(
            bottleneck_stage=None, bottleneck_days=None,
            drop_off_stage=None, drop_off_ratio=None,
            likely_causes=["no pipeline activity yet"],
            recommendations=["confirm req intake completed; activate sourcing"],
        )

    # Build per-stage entry/exit timestamps.
    by_stage: dict[str, list[datetime]] = {}
    transitions = Counter()
    for e in events:
        stage = e.get("stage_to") or e.get("stage")
        when = e.get("occurred_at")
        if not stage or not when:
            continue
        ts = when if isinstance(when, datetime) else datetime.fromisoformat(when)
        by_stage.setdefault(stage, []).append(ts.astimezone(timezone.utc))
        if e.get("stage_from") and e.get("stage_to"):
            transitions[(e["stage_from"], e["stage_to"])] += 1

    # Bottleneck = stage with the most candidates that have been there
    # longer than 7 days without exit.
    bottleneck = max(by_stage.items(), key=lambda kv: len(kv[1]), default=(None, []))
    bottleneck_stage = bottleneck[0]
    bottleneck_days = None
    if bottleneck[1]:
        bottleneck_days = (
            datetime.now(timezone.utc) - min(bottleneck[1])
        ).total_seconds() / 86_400

    # Drop-off = transition with worst conversion (heuristic: pair the
    # outflow of stage X to inflow of next stage).
    drop_off_stage = None
    drop_off_ratio = None
    drop_off_score = -1.0
    stage_order = ["sourcing", "screening", "outreach", "interview", "submission", "offer"]
    for i, stage in enumerate(stage_order[:-1]):
        inflow = len(by_stage.get(stage, []))
        outflow_total = sum(v for (a, _), v in transitions.items() if a == stage)
        if inflow == 0 and outflow_total == 0:
            continue
        denominator = max(inflow, outflow_total, 1)
        out = transitions.get((stage, stage_order[i + 1]), 0)
        ratio = out / denominator
        # Weight by absolute lost candidates so a high-volume 80% drop wins
        # over a zero-volume 100% drop at a tail stage.
        lost = denominator - out
        score = lost * (1.0 - ratio)
        if score > drop_off_score:
            drop_off_score = score
            drop_off_ratio = ratio
            drop_off_stage = stage

    causes: list[str] = []
    recommendations: list[str] = []
    if bottleneck_stage == "screening":
        causes.append("screening throughput too slow — agent backlog or rule failures")
        recommendations.append("check screening agent health and rules-service availability")
    if bottleneck_stage == "outreach":
        causes.append("low response rate on outreach")
        recommendations.append("kick off A/B on subject lines and value-prop opener")
    if bottleneck_stage == "interview":
        causes.append("interview scheduling lag or no-shows")
        recommendations.append("audit calendar integration; tighten scheduling SLA")
    if bottleneck_stage == "submission":
        causes.append("client review queue backed up")
        recommendations.append("escalate to AE; prep submission for hiring manager call")
    if drop_off_ratio is not None and drop_off_ratio < 0.3:
        causes.append(f"low conversion at {drop_off_stage} -> next stage")
        recommendations.append(
            f"investigate {drop_off_stage} disqualification reasons; consider rubric relaxation"
        )

    return StalledDiagnosis(
        bottleneck_stage=bottleneck_stage,
        bottleneck_days=round(bottleneck_days, 2) if bottleneck_days else None,
        drop_off_stage=drop_off_stage,
        drop_off_ratio=round(drop_off_ratio, 4) if drop_off_ratio is not None else None,
        likely_causes=causes,
        recommendations=recommendations,
    )
