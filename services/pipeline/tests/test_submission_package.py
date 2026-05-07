"""Submission-package generator tests."""

from __future__ import annotations

from uuid import uuid4

from pipeline_svc.submission_package import generate
from wfi_schemas import (
    Candidate,
    CandidateSource,
    ClearanceType,
    CompType,
    DimensionScore,
    Recommendation,
    Requisition,
    ReqType,
    Scorecard,
)


def test_package_includes_headline_and_recommendation():
    candidate = Candidate(
        id=uuid4(),
        source=CandidateSource.MANUAL,
        first_name="Sam",
        last_name="Lee",
        email="sam@example.com",
        location_metro="DC Metro",
        location_state="VA",
        clearance_type=ClearanceType.TS_SCI,
    )
    req = Requisition(
        id=uuid4(),
        client_id=uuid4(),
        req_type=ReqType.PRECISION,
        title="Senior Federal AE",
        comp_type=CompType.SALARY,
    )
    sc = Scorecard(
        candidate_id=candidate.id,
        requisition_id=req.id,
        agent="ScreeningAgent",
        model_used="claude-sonnet-4-6",
        qualified=True,
        pass_ratio=0.92,
        recommendation=Recommendation.STRONG_YES,
        confidence=0.9,
        criterion_results=[{"key": "motion", "description": "Enterprise", "passed": True}],
        dimensional_scores=[
            DimensionScore(
                dimension="experience_quality",
                score=4.5,
                reasoning="Long enterprise tenure",
                evidence_quotes=["Senior AE at Datadog 2022-present"],
            ),
        ],
        risk_flags=[],
        summary="Strong fit; clearance current; comp band aligned.",
    )
    pkg = generate(candidate, req, sc)
    assert "Sam Lee" in pkg.headline
    assert "STRONG_YES" in pkg.summary_md or "strong_yes" in pkg.summary_md.lower()
    assert "Datadog" in pkg.detail_md
    assert pkg.recommendation in {"strong_yes", "STRONG_YES"}
    assert pkg.pass_ratio == 0.92
