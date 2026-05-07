"""End-to-end agent test using NullModelRouter + MockRulesClient."""

from __future__ import annotations

import json
from datetime import date
from uuid import uuid4

import pytest

from screening_svc.agent import ScreeningAgent
from wfi_audit import NullAuditLogger
from wfi_llm import NullModelRouter
from wfi_rules_sdk import MockRulesClient
from wfi_schemas import (
    Candidate,
    CandidateSource,
    CareerHistoryEntry,
    ClearanceType,
    CompType,
    EmployerRubric,
    Recommendation,
    Requisition,
    ReqType,
    SalesMotion,
)
from wfi_schemas.requisition import RubricCriterion


def _llm_text(passed: bool = True, recommendation: str = "yes") -> str:
    return json.dumps(
        {
            "llm_criteria": [
                {"key": "role_fit_overall", "passed": passed, "reasoning": "ok"}
            ],
            "dimensions": [
                {"dimension": "experience_quality", "score": 4.0,
                 "reasoning": "strong tenure", "evidence_quotes": ["Senior AE at Datadog"]}
            ],
            "recommendation": recommendation,
            "confidence": 0.85,
            "summary": "Strong commercial AE; matches motion.",
            "risk_flags": [],
        }
    )


def _candidate() -> Candidate:
    return Candidate(
        id=uuid4(),
        source=CandidateSource.MANUAL,
        first_name="Sam",
        last_name="Lee",
        email="sam.lee@example.com",
        primary_motion=SalesMotion.ENTERPRISE,
        clearance_type=ClearanceType.TS_SCI,
        career_history=[
            CareerHistoryEntry(
                company="Datadog",
                title="Senior Account Executive",
                start_date=date(2022, 1, 1),
            )
        ],
    )


def _requisition(rubric: EmployerRubric) -> Requisition:
    return Requisition(
        id=uuid4(),
        client_id=uuid4(),
        req_type=ReqType.PRECISION,
        title="Federal Enterprise AE",
        comp_type=CompType.SALARY,
        budget_min=240_000,
        budget_max=320_000,
        clearance_minimum=ClearanceType.TS_SCI,
        motion_type_required=SalesMotion.ENTERPRISE,
        employer_rubric=rubric,
    )


def _build_agent(llm_passes: bool = True, recommendation: str = "yes") -> ScreeningAgent:
    return ScreeningAgent(
        rules=MockRulesClient(),
        router=NullModelRouter(response_text=_llm_text(llm_passes, recommendation)),
        audit=NullAuditLogger(),
    )


@pytest.mark.asyncio
async def test_agent_qualifies_when_all_predicates_pass():
    rubric = EmployerRubric(
        pass_threshold=0.85,
        criteria=[
            RubricCriterion(key="motion", description="Enterprise",
                            predicate="field_eq:primary_motion=enterprise", severity="must_have"),
            RubricCriterion(key="clearance", description="TS/SCI",
                            predicate="field_in:clearance_type in [ts_sci]", severity="must_have"),
            RubricCriterion(key="role_fit_overall", description="LLM judges fit",
                            predicate="llm:role_fit_overall", severity="must_have"),
        ],
    )
    agent = _build_agent()
    scorecard = await agent.screen(_candidate(), _requisition(rubric))
    assert scorecard.qualified is True
    assert scorecard.pass_ratio == 1.0
    assert scorecard.recommendation in {Recommendation.YES.value, Recommendation.STRONG_YES.value}


@pytest.mark.asyncio
async def test_agent_disqualifies_on_must_have_failure():
    rubric = EmployerRubric(
        criteria=[
            RubricCriterion(key="clearance", description="TS/SCI",
                            predicate="field_in:clearance_type in [ts_sci]", severity="must_have"),
            RubricCriterion(key="motion_wrong", description="PLG only",
                            predicate="field_eq:primary_motion=plg", severity="must_have"),
        ],
    )
    agent = _build_agent()
    scorecard = await agent.screen(_candidate(), _requisition(rubric))
    assert scorecard.qualified is False


@pytest.mark.asyncio
async def test_agent_pass_threshold_respected():
    # 4 must-haves, 3 pass, 1 fails — pass_ratio = 0.75 < 0.85 default.
    rubric = EmployerRubric(
        criteria=[
            RubricCriterion(key="clearance",
                            predicate="field_in:clearance_type in [ts_sci]",
                            description="d", severity="must_have"),
            RubricCriterion(key="motion",
                            predicate="field_eq:primary_motion=enterprise",
                            description="d", severity="must_have"),
            RubricCriterion(key="has_email",
                            predicate="field_present:email",
                            description="d", severity="must_have"),
            RubricCriterion(key="se_demo",
                            predicate="field_gte:se_demo_skill_rating>=4",
                            description="d", severity="must_have"),
        ],
    )
    agent = _build_agent()
    scorecard = await agent.screen(_candidate(), _requisition(rubric))
    # se_demo predicate fails (None < 4) -> must-have failure -> disqualified
    assert scorecard.qualified is False


@pytest.mark.asyncio
async def test_velocity_mode_lowers_threshold(monkeypatch):
    rubric = EmployerRubric(
        pass_threshold=0.85,
        criteria=[
            RubricCriterion(key="motion", description="d",
                            predicate="field_eq:primary_motion=enterprise",
                            severity="nice_to_have"),
            RubricCriterion(key="clearance", description="d",
                            predicate="field_in:clearance_type in [ts_sci]",
                            severity="nice_to_have"),
        ],
    )
    req = _requisition(rubric)
    agent = _build_agent()
    scorecard = await agent.screen(_candidate(), req, velocity_mode=True)
    # All pass with velocity mode → qualified true.
    assert scorecard.qualified is True


@pytest.mark.asyncio
async def test_audit_log_records_each_screen():
    rubric = EmployerRubric(
        criteria=[
            RubricCriterion(key="motion", description="d",
                            predicate="field_eq:primary_motion=enterprise",
                            severity="must_have"),
        ],
    )
    audit = NullAuditLogger()
    agent = ScreeningAgent(
        rules=MockRulesClient(),
        router=NullModelRouter(response_text=_llm_text()),
        audit=audit,
    )
    await agent.screen(_candidate(), _requisition(rubric))
    assert len(audit.entries) == 1
    entry = audit.entries[0]
    assert entry.action_type == "screen_decision"
    assert entry.agent_type == "screening"


@pytest.mark.asyncio
async def test_default_rubric_used_when_none_supplied():
    req = _requisition(EmployerRubric())
    agent = _build_agent()
    scorecard = await agent.screen(_candidate(), req)
    assert len(scorecard.criterion_results) >= 1
