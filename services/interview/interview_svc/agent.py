"""Interview agent.

Two flows:
1. **Async chat interview** — candidate answers in their own time;
   our backend handles state.
2. **Voice interview** — Vapi/Retell drives the call; we receive a
   transcript via webhook.

Both end with the same `evaluate_transcript()` call which routes the
transcript to the frontier tier (Opus) of the model router for a
dimensional scorecard.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import structlog

from interview_svc.rubrics import Dimension, Rubric, for_role
from wfi_audit import AuditLogger, NullAuditLogger
from wfi_llm import ModelRouter, ModelTier, NullModelRouter
from wfi_schemas import (
    ActionType,
    AuditLogEntry,
    DimensionScore,
    EscalationFlag,
    Recommendation,
    Scorecard,
)

log = structlog.get_logger("interview.agent")


@dataclass
class ChatTurn:
    role: str  # interviewer | candidate
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class InterviewSession:
    id: UUID
    candidate_id: UUID
    requisition_id: UUID
    rubric: Rubric
    turns: list[ChatTurn] = field(default_factory=list)
    next_question_index: int = 0
    completed: bool = False


_SYSTEM_PROMPT = """\
You are an experienced recruiter evaluating a candidate against a
role-specific rubric. The candidate has already passed initial screening.

For each dimension below, score 1-5 with EXACTLY this format and return
STRICT JSON only — no markdown, no preamble.

{{
  "dimensions": [
    {{"dimension": "<dimension name>",
      "score": <1.0 to 5.0>,
      "reasoning": "<one sentence>",
      "evidence_quotes": ["<verbatim quote from transcript>", "..."],
      "weight": <weight from rubric>}}
  ],
  "recommendation": "strong_yes"|"yes"|"maybe"|"no"|"strong_no",
  "confidence": <0..1>,
  "summary": "<2-3 sentence overall verdict>",
  "risk_flags": ["<short risk label>"],
  "high_value_candidate": <bool — true if 4+ on every dimension>
}}

Score conservatively. Cite verbatim evidence quotes from the transcript.
Never reward smooth talkers without specifics; never penalise candor.
"""


class InterviewAgent:
    def __init__(
        self,
        *,
        router: ModelRouter | NullModelRouter,
        audit: AuditLogger | NullAuditLogger,
    ) -> None:
        self._router = router
        self._audit = audit

    def start_chat(
        self,
        *,
        candidate_id: UUID,
        requisition_id: UUID,
        role_type: str,
    ) -> InterviewSession:
        rubric = for_role(role_type)
        return InterviewSession(
            id=uuid4(),
            candidate_id=candidate_id,
            requisition_id=requisition_id,
            rubric=rubric,
            turns=[
                ChatTurn(
                    role="interviewer",
                    content=(
                        f"{rubric.intro}\n\n"
                        f"First question: {rubric.dimensions[0].question}"
                    ),
                )
            ],
            next_question_index=1,
        )

    def submit_answer(self, session: InterviewSession, content: str) -> ChatTurn | None:
        session.turns.append(ChatTurn(role="candidate", content=content))
        if session.next_question_index >= len(session.rubric.dimensions):
            session.completed = True
            farewell = ChatTurn(
                role="interviewer",
                content="Thanks — that's everything I need. We'll review and follow up within 48 hours.",
            )
            session.turns.append(farewell)
            return farewell
        question = session.rubric.dimensions[session.next_question_index].question
        session.next_question_index += 1
        next_turn = ChatTurn(role="interviewer", content=question)
        session.turns.append(next_turn)
        return next_turn

    async def evaluate_transcript(
        self,
        *,
        candidate_id: UUID,
        requisition_id: UUID,
        rubric: Rubric,
        transcript: str | list[ChatTurn],
    ) -> Scorecard:
        text = self._render_transcript(transcript)
        rubric_block = json.dumps({
            "role_type": rubric.role_type,
            "intro": rubric.intro,
            "pass_threshold": rubric.pass_threshold,
            "dimensions": [
                {"name": d.name, "question": d.question,
                 "scoring_guide": d.scoring_guide, "weight": d.weight}
                for d in rubric.dimensions
            ],
        }, indent=2)
        start = time.perf_counter()
        response = await self._router.acomplete(
            tier=ModelTier.FRONTIER,  # interview eval is high-stakes
            system=_SYSTEM_PROMPT,
            user=text,
            cached_blocks=[rubric_block],
            max_tokens=2048,
            temperature=0.0,
        )
        try:
            data = json.loads(_strip_code_fence(response.text))
        except json.JSONDecodeError:
            log.warning("interview_eval_unparseable", preview=response.text[:200])
            data = _stub_eval(rubric)

        dims = [DimensionScore(**d) for d in data.get("dimensions", [])]
        weighted_total = sum(d.score * d.weight for d in dims)
        weight_total = sum(d.weight for d in dims) or 1
        weighted_avg = weighted_total / weight_total
        qualified = weighted_avg >= rubric.pass_threshold
        escalations: list[EscalationFlag] = []
        if data.get("high_value_candidate"):
            escalations.append(EscalationFlag.HIGH_VALUE_INTERVIEW)
        # Mixed-signals escalation: variance > 1 across dimensions
        if dims and (max(d.score for d in dims) - min(d.score for d in dims) >= 2.5):
            escalations.append(EscalationFlag.MIXED_SIGNALS)

        scorecard = Scorecard(
            candidate_id=candidate_id,
            requisition_id=requisition_id,
            agent="InterviewAgent",
            model_used=getattr(self._router, "model_for", lambda t: "null")(ModelTier.FRONTIER),
            qualified=qualified,
            pass_ratio=round(weighted_avg / 5.0, 4),
            recommendation=Recommendation(data.get("recommendation", "maybe")),
            confidence=float(data.get("confidence", 0.5)),
            criterion_results=[],
            dimensional_scores=dims,
            risk_flags=list(data.get("risk_flags", [])),
            escalations=escalations,
            summary=data.get("summary", ""),
            input_summary=f"transcript_len={len(text)}, role={rubric.role_type}",
            cost_usd=response.cost_usd,
            latency_ms=int((time.perf_counter() - start) * 1000),
        )
        await self._audit.record(
            AuditLogEntry(
                action_type=ActionType.INTERVIEW_EVALUATION,
                candidate_id=candidate_id,
                requisition_id=requisition_id,
                agent_type="interview",
                model_used=scorecard.model_used,
                input_summary=scorecard.input_summary,
                decision="qualified" if qualified else "disqualified",
                reasoning=f"weighted_avg={weighted_avg:.2f} threshold={rubric.pass_threshold}",
                confidence_score=scorecard.confidence,
                cost_usd=scorecard.cost_usd,
                latency_ms=scorecard.latency_ms,
            )
        )
        return scorecard

    @staticmethod
    def _render_transcript(transcript: str | list[ChatTurn]) -> str:
        if isinstance(transcript, str):
            return transcript
        return "\n".join(f"{t.role.upper()}: {t.content}" for t in transcript)


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


def _stub_eval(rubric: Rubric) -> dict[str, Any]:
    """Deterministic fallback when the model returns junk."""
    return {
        "dimensions": [
            {
                "dimension": d.name,
                "score": 3.0,
                "reasoning": "evaluator returned unparseable output; defaulting to mid-tier score",
                "evidence_quotes": [],
                "weight": d.weight,
            }
            for d in rubric.dimensions
        ],
        "recommendation": "maybe",
        "confidence": 0.3,
        "summary": "Evaluator output could not be parsed; manual review recommended.",
        "risk_flags": ["llm_parse_failure"],
        "high_value_candidate": False,
    }
