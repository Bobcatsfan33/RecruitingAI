"""Pydantic schema invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from wfi_schemas import (
    Candidate,
    CandidateSource,
    Citizenship,
    ClearanceType,
    EngagementSignals,
)


def test_candidate_lowercases_email():
    c = Candidate(
        source=CandidateSource.MANUAL,
        first_name="A",
        last_name="B",
        email="MIXED@Case.Example.COM",
    )
    assert c.email == "mixed@case.example.com"


def test_candidate_must_have_first_and_last_name():
    with pytest.raises(ValidationError):
        Candidate(source=CandidateSource.MANUAL, first_name="", last_name="B", email="a@b.local")


def test_engagement_score_bounds():
    with pytest.raises(ValidationError):
        EngagementSignals(approachability_score=120)
    with pytest.raises(ValidationError):
        EngagementSignals(counteroffer_risk_score=-1)


def test_has_contact_requires_at_least_one_channel():
    c = Candidate(
        source=CandidateSource.MANUAL,
        first_name="A",
        last_name="B",
        email="a@b.local",
    )
    assert c.has_contact()
    c.email = None
    assert not c.has_contact()
    c.linkedin_url = "https://linkedin.com/in/a"
    assert c.has_contact()


def test_default_citizenship_unknown():
    c = Candidate(
        source=CandidateSource.MANUAL,
        first_name="A",
        last_name="B",
        email="a@b.local",
    )
    assert c.citizenship == Citizenship.UNKNOWN.value


def test_clearance_default_none():
    c = Candidate(
        source=CandidateSource.MANUAL,
        first_name="A",
        last_name="B",
        email="a@b.local",
    )
    assert c.clearance_type == ClearanceType.NONE.value
