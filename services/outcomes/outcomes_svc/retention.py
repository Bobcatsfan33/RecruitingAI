"""90-day retention tracking + hiring-manager satisfaction scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class RetentionWindow(str, Enum):
    DAY_30 = "day_30"
    DAY_60 = "day_60"
    DAY_90 = "day_90"


@dataclass
class RetentionSurvey:
    id: UUID
    candidate_id: UUID
    requisition_id: UUID
    window: RetentionWindow
    sent_at: datetime
    candidate_response: dict[str, Any] | None = None
    hiring_manager_response: dict[str, Any] | None = None
    label: str | None = None  # placed | falloff | terminated


@dataclass
class SatisfactionScore:
    candidate_id: UUID
    requisition_id: UUID
    candidate_score: float | None
    hiring_manager_score: float | None
    average: float | None
    notes: str = ""


def schedule_surveys(
    *,
    candidate_id: UUID,
    requisition_id: UUID,
    placement_date: datetime,
) -> list[RetentionSurvey]:
    """Build 30/60/90 day surveys to fire in sequence."""
    return [
        RetentionSurvey(
            id=uuid4(),
            candidate_id=candidate_id,
            requisition_id=requisition_id,
            window=window,
            sent_at=placement_date + timedelta(days=days),
        )
        for window, days in (
            (RetentionWindow.DAY_30, 30),
            (RetentionWindow.DAY_60, 60),
            (RetentionWindow.DAY_90, 90),
        )
    ]


def score_satisfaction(survey: RetentionSurvey) -> SatisfactionScore:
    candidate_score = _score(survey.candidate_response)
    hm_score = _score(survey.hiring_manager_response)
    if candidate_score is None and hm_score is None:
        average = None
    else:
        scores = [s for s in (candidate_score, hm_score) if s is not None]
        average = sum(scores) / len(scores)
    return SatisfactionScore(
        candidate_id=survey.candidate_id,
        requisition_id=survey.requisition_id,
        candidate_score=candidate_score,
        hiring_manager_score=hm_score,
        average=round(average, 2) if average is not None else None,
    )


def _score(response: dict[str, Any] | None) -> float | None:
    if not response:
        return None
    raw = response.get("score")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def label_survey(
    survey: RetentionSurvey, *, still_employed: bool, voluntary_termination: bool = False,
) -> RetentionSurvey:
    if not still_employed and voluntary_termination:
        survey.label = "falloff"
    elif not still_employed:
        survey.label = "terminated"
    else:
        survey.label = "placed"
    return survey
