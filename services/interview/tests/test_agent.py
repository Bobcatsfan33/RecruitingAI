"""Interview agent — chat flow + transcript evaluation."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from interview_svc.agent import ChatTurn, InterviewAgent
from interview_svc.rubrics import for_role
from wfi_audit import NullAuditLogger
from wfi_llm import NullModelRouter


def _llm_text(*, recommendation: str = "yes", high_value: bool = False) -> str:
    return json.dumps({
        "dimensions": [
            {"dimension": "deal_narrative", "score": 4.0,
             "reasoning": "specific named deals", "evidence_quotes": ["closed $1.2M Acme deal"], "weight": 1.5},
            {"dimension": "strategic_thinking", "score": 4.0,
             "reasoning": "clear territory plan", "evidence_quotes": [], "weight": 1.2},
            {"dimension": "objection_handling", "score": 3.5,
             "reasoning": "acknowledged failures", "evidence_quotes": [], "weight": 1.0},
            {"dimension": "communication_clarity", "score": 4.0,
             "reasoning": "no jargon", "evidence_quotes": [], "weight": 1.0},
            {"dimension": "quota_validation", "score": 5.0,
             "reasoning": "exact W-2 numbers provided", "evidence_quotes": ["$1.2M attainment 2024"], "weight": 1.3},
        ],
        "recommendation": recommendation,
        "confidence": 0.85,
        "summary": "Strong commercial AE with verified comp.",
        "risk_flags": [],
        "high_value_candidate": high_value,
    })


def _agent(*, llm_text: str | None = None) -> InterviewAgent:
    return InterviewAgent(
        router=NullModelRouter(response_text=llm_text or _llm_text()),
        audit=NullAuditLogger(),
    )


def test_chat_walks_through_dimensions_in_order():
    agent = _agent()
    session = agent.start_chat(
        candidate_id=uuid4(), requisition_id=uuid4(), role_type="sales",
    )
    rubric = for_role("sales")
    # First question already in the session.
    assert rubric.dimensions[0].question in session.turns[0].content
    # Answer + next.
    next_turn = agent.submit_answer(session, "$1.2M attainment in 2024.")
    assert rubric.dimensions[1].question in next_turn.content


def test_chat_terminates_after_all_dimensions():
    agent = _agent()
    session = agent.start_chat(candidate_id=uuid4(), requisition_id=uuid4(), role_type="sales")
    for _ in range(len(session.rubric.dimensions)):
        agent.submit_answer(session, "answer")
    assert session.completed


@pytest.mark.asyncio
async def test_evaluate_transcript_returns_qualified_scorecard():
    agent = _agent()
    rubric = for_role("sales")
    scorecard = await agent.evaluate_transcript(
        candidate_id=uuid4(),
        requisition_id=uuid4(),
        rubric=rubric,
        transcript="INTERVIEWER: ...\nCANDIDATE: $1.2M attainment.",
    )
    assert scorecard.qualified is True
    assert scorecard.recommendation in ("yes", "strong_yes")
    assert len(scorecard.dimensional_scores) == len(rubric.dimensions)


@pytest.mark.asyncio
async def test_high_value_flag_triggers_escalation():
    agent = _agent(llm_text=_llm_text(high_value=True))
    rubric = for_role("sales")
    sc = await agent.evaluate_transcript(
        candidate_id=uuid4(), requisition_id=uuid4(),
        rubric=rubric, transcript="...",
    )
    assert "high_value_interview" in sc.escalations


@pytest.mark.asyncio
async def test_audit_log_records_interview():
    audit = NullAuditLogger()
    agent = InterviewAgent(
        router=NullModelRouter(response_text=_llm_text()),
        audit=audit,
    )
    rubric = for_role("sales")
    await agent.evaluate_transcript(
        candidate_id=uuid4(), requisition_id=uuid4(),
        rubric=rubric, transcript="...",
    )
    assert any(e.action_type == "interview_evaluation" for e in audit.entries)


@pytest.mark.asyncio
async def test_unparseable_llm_returns_stub():
    agent = InterviewAgent(
        router=NullModelRouter(response_text="not json at all"),
        audit=NullAuditLogger(),
    )
    rubric = for_role("sales")
    sc = await agent.evaluate_transcript(
        candidate_id=uuid4(), requisition_id=uuid4(),
        rubric=rubric, transcript="...",
    )
    assert "llm_parse_failure" in sc.risk_flags
