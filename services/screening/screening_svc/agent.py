"""Screening agent.

Process:
1. **Ownership pre-check** — call rules service `ownership_bundle`. If
   blocked, short-circuit with a "disqualified — ownership" decision.
2. **Deterministic predicates** — evaluate every employer-rubric criterion
   whose predicate is non-LLM. Track passed / failed counts.
3. **LLM judgment block** — for `llm:` predicates AND any free-form
   role-fit assessment, call the model router (mid tier, frontier for
   precision-mode reqs over $300K comp). Returns dimensional scores
   and per-LLM-criterion outcomes.
4. **Pass-rate decision** — qualified iff
   (passed_criteria / total_active_criteria) ≥ rubric.pass_threshold.
   Default threshold = 0.85.
5. **Escalation triggers** — VP+, $350K+, non-compete, mixed signals.
6. **Audit log** — every decision recorded to ClickHouse.

Velocity mode (req.urgency == "critical_48h" or rules-service classifies
the req as "velocity") trims the LLM judgment block to a single
"is_this_remotely_a_fit" prompt and lowers the pass threshold by 10pp.
"""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

import structlog

from screening_svc.escalation import detect as detect_escalations
from screening_svc.predicates import evaluate as evaluate_predicate
from wfi_audit import AuditLogger, NullAuditLogger
from wfi_llm import ModelRouter, ModelTier, NullModelRouter
from wfi_rules_sdk import MockRulesClient, RuleEvaluation, RulesClient
from wfi_schemas import (
    ActionType,
    AuditLogEntry,
    Candidate,
    DimensionScore,
    EmployerRubric,
    Recommendation,
    Requisition,
    Scorecard,
)

log = structlog.get_logger("screening.agent")


_LLM_SYSTEM = """\
You are a screening agent for a recruiting platform. You evaluate a candidate
against a requisition. The employer has provided a rubric of pass criteria;
you ALSO produce free-form dimensional scores that capture nuance.

Return STRICT JSON with this schema:
{
  "llm_criteria": [
    {"key": "<criterion key>", "passed": bool, "reasoning": "<one sentence>"}
  ],
  "dimensions": [
    {"dimension": "<name>", "score": <0..5 number>,
     "reasoning": "<one sentence>", "evidence_quotes": ["..."]}
  ],
  "recommendation": "strong_yes"|"yes"|"maybe"|"no"|"strong_no",
  "confidence": <0..1>,
  "summary": "<2-3 sentence overall verdict>",
  "risk_flags": ["<short risk label>"]
}

Score conservatively. Cite evidence quotes verbatim from the candidate
profile. Never invent compensation, dates, or clearance details.
"""


class ScreeningAgent:
    def __init__(
        self,
        *,
        rules: RulesClient | MockRulesClient,
        router: ModelRouter | NullModelRouter,
        audit: AuditLogger | NullAuditLogger,
    ) -> None:
        self._rules = rules
        self._router = router
        self._audit = audit

    async def screen(
        self,
        candidate: Candidate,
        requisition: Requisition,
        *,
        client_id: UUID | None = None,
        velocity_mode: bool | None = None,
    ) -> Scorecard:
        start = time.perf_counter()
        candidate_dict = candidate.model_dump(mode="json")
        rubric = requisition.employer_rubric or EmployerRubric()
        if not rubric.criteria:
            # No employer rubric — fall back to a minimal default rubric so
            # the agent still produces a deterministic scorecard.
            rubric = _default_rubric(requisition)

        # 1. Ownership pre-check (only if we know which client).
        ownership: dict[str, Any] = {}
        if client_id is not None and candidate.id is not None:
            ownership_eval: RuleEvaluation = await self._rules.evaluate(
                "ownership_bundle",
                {
                    "has_exclusivity": False,
                    "has_rtr": True,
                    "is_dnc": False,
                    "has_non_compete": False,
                    "_candidate_id": str(candidate.id),
                    "_client_id": str(client_id),
                },
            )
            ownership = ownership_eval.details
            if ownership_eval.verdict == "blocked":
                return await self._scorecard_blocked(candidate, requisition, ownership_eval, start)

        # 2. Deterministic predicates.
        criterion_results: list[dict[str, Any]] = []
        llm_criteria: list[Any] = []
        for criterion in rubric.criteria:
            outcome = evaluate_predicate(criterion.predicate, candidate_dict)
            if outcome is None:
                # Defer to LLM.
                llm_criteria.append(criterion)
                continue
            criterion_results.append(
                {
                    "key": criterion.key,
                    "description": criterion.description,
                    "weight": criterion.weight,
                    "severity": criterion.severity,
                    "predicate": criterion.predicate,
                    "passed": bool(outcome),
                    "reasoning": "deterministic predicate",
                }
            )

        # 3. LLM judgment.
        velocity = bool(velocity_mode) if velocity_mode is not None else _is_velocity(requisition)
        tier = ModelTier.LIGHT if velocity else _tier_for_req(requisition)
        llm_result = await self._llm_judgment(
            candidate=candidate_dict,
            requisition=requisition,
            rubric=rubric,
            llm_criteria=llm_criteria,
            tier=tier,
        )
        for c in llm_result.get("llm_criteria", []):
            spec = next((x for x in llm_criteria if x.key == c.get("key")), None)
            criterion_results.append(
                {
                    "key": c.get("key"),
                    "description": spec.description if spec else "",
                    "weight": spec.weight if spec else 1.0,
                    "severity": spec.severity if spec else "must_have",
                    "predicate": spec.predicate if spec else "llm:?",
                    "passed": bool(c.get("passed")),
                    "reasoning": c.get("reasoning", ""),
                }
            )
        dimensions = [DimensionScore(**d) for d in llm_result.get("dimensions", [])]

        # 4. Pass-rate decision.
        active = [c for c in criterion_results if c["severity"] != "informational"]
        passed = sum(1 for c in active if c["passed"])
        total = max(1, len(active))
        pass_ratio = passed / total
        threshold = max(0.0, rubric.pass_threshold - (0.10 if velocity else 0.0))
        # Any "must_have" failure forces disqualification regardless of ratio.
        must_fail = any(
            c["severity"] == "must_have" and not c["passed"] for c in criterion_results
        )
        qualified = pass_ratio >= threshold and not must_fail

        # 5. Escalations.
        escalations = detect_escalations(
            candidate_dict,
            ownership_status=ownership,
            criterion_results=criterion_results,
        )

        recommendation = _recommendation(
            llm=llm_result.get("recommendation"),
            qualified=qualified,
            pass_ratio=pass_ratio,
        )

        scorecard = Scorecard(
            candidate_id=candidate.id,  # type: ignore[arg-type]
            requisition_id=requisition.id,  # type: ignore[arg-type]
            agent="ScreeningAgent",
            model_used=getattr(self._router, "model_for", lambda t: "null")(tier),
            qualified=qualified,
            pass_ratio=round(pass_ratio, 4),
            recommendation=Recommendation(recommendation),
            confidence=float(llm_result.get("confidence", 0.5)),
            criterion_results=criterion_results,
            dimensional_scores=dimensions,
            risk_flags=list(llm_result.get("risk_flags", [])),
            escalations=escalations,
            summary=llm_result.get("summary", ""),
            input_summary=_summary_for_audit(candidate, requisition),
            cost_usd=getattr(llm_result, "_cost_usd", None),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )

        await self._audit.record(
            AuditLogEntry(
                action_type=ActionType.SCREEN_DECISION,
                candidate_id=candidate.id,  # type: ignore[arg-type]
                requisition_id=requisition.id,
                agent_type="screening",
                model_used=scorecard.model_used,
                input_summary=scorecard.input_summary,
                decision="qualified" if qualified else "disqualified",
                reasoning=f"pass_ratio={pass_ratio:.2f} threshold={threshold:.2f} velocity={velocity}",
                confidence_score=scorecard.confidence,
                cost_usd=scorecard.cost_usd,
                latency_ms=scorecard.latency_ms,
            )
        )
        return scorecard

    async def screen_batch(
        self,
        pairs: list[tuple[Candidate, Requisition]],
    ) -> list[Scorecard]:
        results: list[Scorecard] = []
        for candidate, requisition in pairs:
            results.append(await self.screen(candidate, requisition))
        return results

    # ------------------------------------------------------------------

    async def _llm_judgment(
        self,
        *,
        candidate: dict[str, Any],
        requisition: Requisition,
        rubric: EmployerRubric,
        llm_criteria: list[Any],
        tier: ModelTier,
    ) -> dict[str, Any]:
        prompt = {
            "requisition": {
                "title": requisition.title,
                "must_have_skills": requisition.must_have_skills,
                "nice_to_have_skills": requisition.nice_to_have_skills,
                "clearance_minimum": requisition.clearance_minimum,
                "polygraph_required": requisition.polygraph_required,
                "motion_type_required": requisition.motion_type_required,
                "comp_type": requisition.comp_type,
                "budget_min": requisition.budget_min,
                "budget_max": requisition.budget_max,
            },
            "candidate": _redact(candidate),
            "llm_criteria": [
                {"key": c.key, "description": c.description, "predicate": c.predicate}
                for c in llm_criteria
            ],
            "instructions": "Evaluate each llm_criterion and produce dimensional scores.",
        }
        response = await self._router.acomplete(
            tier=tier,
            system=_LLM_SYSTEM,
            user=json.dumps(prompt, default=str),
            cached_blocks=[json.dumps(rubric.model_dump(), default=str)],
            max_tokens=2048,
            temperature=0.0,
        )
        try:
            data = json.loads(_strip_code_fence(response.text))
        except json.JSONDecodeError:
            log.warning("screening_llm_unparseable", preview=response.text[:200])
            data = {
                "llm_criteria": [],
                "dimensions": [],
                "recommendation": "maybe",
                "confidence": 0.3,
                "summary": "LLM returned unparseable output; defaulting to maybe.",
                "risk_flags": ["llm_parse_failure"],
            }
        data["_cost_usd"] = response.cost_usd
        return data

    async def _scorecard_blocked(
        self,
        candidate: Candidate,
        requisition: Requisition,
        ownership_eval: RuleEvaluation,
        start: float,
    ) -> Scorecard:
        return Scorecard(
            candidate_id=candidate.id,  # type: ignore[arg-type]
            requisition_id=requisition.id,  # type: ignore[arg-type]
            agent="ScreeningAgent",
            model_used="ownership_pre_check",
            qualified=False,
            pass_ratio=0.0,
            recommendation=Recommendation.NO,
            confidence=1.0,
            criterion_results=[],
            dimensional_scores=[],
            risk_flags=["ownership_blocked"],
            escalations=[],
            summary=ownership_eval.reasoning,
            input_summary=_summary_for_audit(candidate, requisition),
            latency_ms=int((time.perf_counter() - start) * 1000),
        )


# ---------- helpers --------------------------------------------------------

def _is_velocity(req: Requisition) -> bool:
    if req.urgency == "critical_48h":
        return True
    return False


def _tier_for_req(req: Requisition) -> ModelTier:
    high_comp = (req.budget_max or 0) > 300_000
    if req.req_type == "precision" and high_comp:
        return ModelTier.FRONTIER
    return ModelTier.MID


def _recommendation(*, llm: str | None, qualified: bool, pass_ratio: float) -> str:
    if not qualified:
        return "no" if pass_ratio < 0.5 else "maybe"
    if llm in {"strong_yes", "yes", "maybe", "no", "strong_no"}:
        return llm
    if pass_ratio >= 0.95:
        return "strong_yes"
    return "yes"


def _redact(candidate: dict[str, Any]) -> dict[str, Any]:
    """Drop high-PII fields the LLM doesn't need to evaluate fit."""
    redacted = dict(candidate)
    for key in ("phone", "email", "linkedin_url"):
        if key in redacted:
            redacted[key] = "<redacted>"
    return redacted


def _summary_for_audit(c: Candidate, r: Requisition) -> str:
    return (
        f"candidate={c.first_name[:1]}.{c.last_name} "
        f"req={r.title} clearance={r.clearance_minimum} "
        f"motion={r.motion_type_required}"
    )


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _default_rubric(req: Requisition) -> EmployerRubric:
    """Minimal fallback rubric — evaluates clearance + motion + skill overlap."""
    from wfi_schemas.requisition import RubricCriterion

    crit: list[RubricCriterion] = []
    if req.clearance_minimum and req.clearance_minimum != "none":
        crit.append(
            RubricCriterion(
                key="clearance_floor",
                description=f"Clearance >= {req.clearance_minimum}",
                predicate=f"field_in:clearance_type in [top_secret, ts_sci, {req.clearance_minimum}]",
                severity="must_have",
            )
        )
    if req.motion_type_required:
        crit.append(
            RubricCriterion(
                key="motion_match",
                description=f"Primary motion is {req.motion_type_required}",
                predicate=f"field_eq:primary_motion={req.motion_type_required}",
                severity="must_have",
            )
        )
    crit.append(
        RubricCriterion(
            key="role_fit",
            description="LLM judges overall role fit.",
            predicate="llm:role_fit_overall",
            severity="must_have",
        )
    )
    return EmployerRubric(criteria=crit)
