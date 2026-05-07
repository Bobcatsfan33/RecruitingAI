"""Embedding text builders are pure functions — easy to test."""

from __future__ import annotations

from uuid import uuid4

from candidates_svc.embeddings_text import (
    candidate_embedding_text,
    requisition_embedding_text,
)
from wfi_schemas import (
    Candidate,
    CandidateSource,
    ClearanceType,
    CompType,
    PolygraphType,
    Requisition,
    ReqType,
    SalesMotion,
)


def test_candidate_text_includes_name_and_metro():
    c = Candidate(
        source=CandidateSource.MANUAL,
        first_name="Sam",
        last_name="Lee",
        email="s@l.local",
        location_metro="DC Metro",
        location_state="VA",
        primary_motion=SalesMotion.ENTERPRISE,
        clearance_type=ClearanceType.TS_SCI,
        polygraph=PolygraphType.CI,
    )
    text = candidate_embedding_text(c)
    assert "Sam Lee" in text
    assert "DC Metro" in text
    assert "TS SCI" in text
    assert "CI" in text
    assert "enterprise" in text.lower()


def test_requisition_text_includes_skills_and_clearance():
    r = Requisition(
        client_id=uuid4(),
        req_type=ReqType.PRECISION,
        title="Federal SE",
        comp_type=CompType.SALARY,
        clearance_minimum=ClearanceType.TS_SCI,
        polygraph_required=PolygraphType.FULL_SCOPE,
        must_have_skills=["MEDDIC", "Splunk"],
        nice_to_have_skills=["AWS"],
        years_experience_min=5,
    )
    text = requisition_embedding_text(r)
    assert "Federal SE" in text
    assert "TS SCI" in text
    assert "FULL SCOPE" in text
    assert "MEDDIC" in text
    assert "5 years" in text
