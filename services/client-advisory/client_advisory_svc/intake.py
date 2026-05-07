"""Intake feasibility analyzer.

Run on a new requisition: combine the rules-engine verdicts (comp,
timeline, requirement-feasibility) into a single client-facing
"feasibility report" with relaxation recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from wfi_rules_sdk import MockRulesClient, RulesClient
from wfi_schemas import Requisition


@dataclass
class FeasibilityReport:
    overall_verdict: str  # feasible | difficult | infeasible
    rule_results: list[dict[str, Any]] = field(default_factory=list)
    market_data: dict[str, Any] = field(default_factory=dict)
    relaxation_options: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


async def analyze(
    requisition: Requisition,
    *,
    rules: RulesClient | MockRulesClient,
    market_lookup: dict[str, Any] | None = None,
) -> FeasibilityReport:
    market_lookup = market_lookup or {}
    role_type = (requisition.title or "").split()[-1].lower() if requisition.title else "ae"
    seniority = "senior" if (requisition.years_experience_min or 0) >= 7 else "mid"
    location = requisition.location_requirements.get("metro") or "DC Metro"
    clearance_level = requisition.clearance_minimum

    comp_inputs = {
        "role_type": role_type,
        "seniority": seniority,
        "location": location,
        "clearance_level": clearance_level,
        "client_budget": requisition.budget_max or requisition.budget_min or 0,
        "market_rate": market_lookup.get("market_rate"),
    }
    timeline_inputs = {
        "clearance_requirement": requisition.clearance_minimum,
        "new_investigation_required": requisition.role_specific_requirements.get(
            "new_investigation_required", False
        ),
        "timeline_days": requisition.sla_days_to_fill or 90,
        "role_complexity": requisition.role_specific_requirements.get("role_complexity", 5),
    }

    comp_result = await rules.evaluate("comp_market_alignment", comp_inputs)
    timeline_result = await rules.evaluate("timeline_reasonableness", timeline_inputs)

    rule_results = [comp_result.model_dump(), timeline_result.model_dump()]

    overall = _roll_up([comp_result.verdict, timeline_result.verdict])
    relaxations = _build_relaxations(comp_result, timeline_result, requisition)

    summary = _summary(overall, comp_result, timeline_result)
    return FeasibilityReport(
        overall_verdict=overall,
        rule_results=rule_results,
        market_data=market_lookup,
        relaxation_options=relaxations,
        summary=summary,
    )


def _roll_up(verdicts: list[str]) -> str:
    if "infeasible" in verdicts:
        return "infeasible"
    if "warning" in verdicts or "difficult" in verdicts:
        return "difficult"
    return "feasible"


def _build_relaxations(comp_result, timeline_result, req: Requisition) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    if comp_result.verdict in ("infeasible", "warning"):
        options.append({
            "lever": "comp",
            "current": req.budget_max,
            "suggestion": "Increase budget toward market rate (see comp.suggestions).",
        })
    if timeline_result.verdict in ("infeasible", "warning"):
        options.append({
            "lever": "timeline",
            "current": req.sla_days_to_fill,
            "suggestion": "Extend timeline OR shift to candidates with active clearance only.",
        })
    if req.clearance_minimum in ("ts_sci",):
        options.append({
            "lever": "clearance",
            "current": req.clearance_minimum,
            "suggestion": "Relax to TS — addressable pool typically increases ~4x.",
        })
    if req.location_requirements.get("onsite"):
        options.append({
            "lever": "location",
            "current": "onsite",
            "suggestion": "Allow hybrid 2 days/wk — addressable pool typically doubles in cleared markets.",
        })
    return options


def _summary(overall: str, comp_result, timeline_result) -> str:
    return (
        f"Overall: **{overall.upper()}**.\n\n"
        f"- Comp: {comp_result.verdict} — {comp_result.reasoning}\n"
        f"- Timeline: {timeline_result.verdict} — {timeline_result.reasoning}"
    )
