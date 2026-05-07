"""Deployability score behaviour."""

from __future__ import annotations

from datetime import date, timedelta

from candidates_svc.deployability import deployability_score
from wfi_schemas import (
    AvailabilityWindow,
    Candidate,
    CandidateSource,
    Citizenship,
    ClearanceStatus,
    ClearanceType,
    EngagementSignals,
    PolygraphType,
)


def _base() -> Candidate:
    return Candidate(
        source=CandidateSource.MANUAL,
        first_name="Test",
        last_name="User",
        email="t@u.local",
    )


def test_uncleared_candidate_scores_low():
    c = _base()
    assert deployability_score(c) <= 5


def test_active_ts_sci_with_lifestyle_poly_scores_high():
    c = _base()
    c.clearance_type = ClearanceType.TS_SCI.value
    c.polygraph = PolygraphType.LIFESTYLE.value
    c.clearance_status = ClearanceStatus.ACTIVE.value
    c.adjudication_date = date.today() - timedelta(days=180)
    c.read_on_history = [{"program": "X"}, {"program": "Y"}, {"program": "Z"}, {"program": "Q"}, {"program": "R"}]
    c.itar_ear_eligible = True
    c.citizenship = Citizenship.US_CITIZEN.value
    c.engagement = EngagementSignals(availability_window=AvailabilityWindow.IMMEDIATELY)
    score = deployability_score(c)
    assert score >= 80


def test_expired_clearance_scored_lower_than_active():
    c1, c2 = _base(), _base()
    for c in (c1, c2):
        c.clearance_type = ClearanceType.SECRET.value
        c.citizenship = Citizenship.US_CITIZEN.value
    c1.clearance_status = ClearanceStatus.ACTIVE.value
    c2.clearance_status = ClearanceStatus.EXPIRED.value
    assert deployability_score(c1) > deployability_score(c2)


def test_target_poly_match_increases_score():
    c = _base()
    c.clearance_type = ClearanceType.TS_SCI.value
    c.polygraph = PolygraphType.FULL_SCOPE.value
    c.clearance_status = ClearanceStatus.ACTIVE.value
    c.citizenship = Citizenship.US_CITIZEN.value
    no_target = deployability_score(c)
    matched = deployability_score(c, target_poly=PolygraphType.FULL_SCOPE)
    # Matching the requested poly should at least equal generic poly bonus
    assert matched >= no_target
