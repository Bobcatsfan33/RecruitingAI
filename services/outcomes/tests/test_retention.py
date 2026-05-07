"""Retention survey scheduling + scoring."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from outcomes_svc.retention import (
    RetentionSurvey,
    RetentionWindow,
    label_survey,
    schedule_surveys,
    score_satisfaction,
)


def test_schedule_creates_30_60_90_surveys():
    placed = datetime(2026, 5, 1, tzinfo=timezone.utc)
    surveys = schedule_surveys(
        candidate_id=uuid4(),
        requisition_id=uuid4(),
        placement_date=placed,
    )
    assert [s.window for s in surveys] == [
        RetentionWindow.DAY_30,
        RetentionWindow.DAY_60,
        RetentionWindow.DAY_90,
    ]
    assert surveys[0].sent_at == placed + timedelta(days=30)
    assert surveys[2].sent_at == placed + timedelta(days=90)


def test_satisfaction_averages_two_responses():
    survey = RetentionSurvey(
        id=uuid4(),
        candidate_id=uuid4(),
        requisition_id=uuid4(),
        window=RetentionWindow.DAY_30,
        sent_at=datetime.now(timezone.utc),
        candidate_response={"score": 4.0},
        hiring_manager_response={"score": 5.0},
    )
    score = score_satisfaction(survey)
    assert score.average == 4.5


def test_satisfaction_handles_missing_response():
    survey = RetentionSurvey(
        id=uuid4(),
        candidate_id=uuid4(),
        requisition_id=uuid4(),
        window=RetentionWindow.DAY_30,
        sent_at=datetime.now(timezone.utc),
        candidate_response={"score": 3.0},
    )
    score = score_satisfaction(survey)
    assert score.candidate_score == 3.0
    assert score.hiring_manager_score is None
    assert score.average == 3.0


def test_label_survey_distinguishes_falloff_from_termination():
    base = RetentionSurvey(
        id=uuid4(), candidate_id=uuid4(), requisition_id=uuid4(),
        window=RetentionWindow.DAY_30, sent_at=datetime.now(timezone.utc),
    )
    placed = label_survey(base, still_employed=True)
    falloff = label_survey(
        RetentionSurvey(id=uuid4(), candidate_id=uuid4(), requisition_id=uuid4(),
                        window=RetentionWindow.DAY_30, sent_at=datetime.now(timezone.utc)),
        still_employed=False, voluntary_termination=True,
    )
    terminated = label_survey(
        RetentionSurvey(id=uuid4(), candidate_id=uuid4(), requisition_id=uuid4(),
                        window=RetentionWindow.DAY_30, sent_at=datetime.now(timezone.utc)),
        still_employed=False, voluntary_termination=False,
    )
    assert placed.label == "placed"
    assert falloff.label == "falloff"
    assert terminated.label == "terminated"
