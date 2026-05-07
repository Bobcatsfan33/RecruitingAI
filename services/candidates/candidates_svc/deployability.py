"""Deployability scoring (0-100) for cleared candidates.

Inputs come from the candidate record. Higher score = closer to deployable
on a cleared contract today. Pure function, no I/O.

Scoring buckets:
- Clearance currency (40 points): active > interim > expired > none
- Polygraph alignment (15 points): match the requested poly level
- Investigation freshness (15 points): newer adjudication = higher score
- Read-on history (10 points): more agencies / programs = higher
- Citizenship (10 points): US citizen for cleared work
- ITAR/EAR eligibility (5 points)
- Availability (5 points): immediate > 2wk > 30d > not_looking
"""

from __future__ import annotations

from datetime import date, timedelta

from wfi_schemas import (
    AvailabilityWindow,
    Candidate,
    Citizenship,
    ClearanceStatus,
    ClearanceType,
    PolygraphType,
)


def deployability_score(c: Candidate, *, target_poly: PolygraphType | None = None) -> int:
    score = 0

    # 1. Clearance currency
    clearance_points = {
        ClearanceType.NONE: 0,
        ClearanceType.PUBLIC_TRUST: 10,
        ClearanceType.SECRET: 20,
        ClearanceType.TOP_SECRET: 30,
        ClearanceType.TS_SCI: 40,
    }
    base = clearance_points[ClearanceType(c.clearance_type)]
    if c.clearance_status == ClearanceStatus.ACTIVE.value:
        score += base
    elif c.clearance_status == ClearanceStatus.INTERIM.value:
        score += int(base * 0.75)
    elif c.clearance_status == ClearanceStatus.EXPIRED.value:
        score += int(base * 0.4)
    elif c.clearance_status == ClearanceStatus.IN_PROCESS.value:
        score += int(base * 0.5)

    # 2. Polygraph alignment
    poly_rank = {
        PolygraphType.NONE: 0,
        PolygraphType.CI: 1,
        PolygraphType.FULL_SCOPE: 2,
        PolygraphType.LIFESTYLE: 3,
    }
    candidate_poly = PolygraphType(c.polygraph)
    if target_poly is None:
        score += poly_rank[candidate_poly] * 5
    elif poly_rank[candidate_poly] >= poly_rank[target_poly]:
        score += 15
    elif poly_rank[candidate_poly] == poly_rank[target_poly] - 1:
        score += 8

    # 3. Investigation freshness
    if c.adjudication_date:
        age = (date.today() - c.adjudication_date)
        if age < timedelta(days=2 * 365):
            score += 15
        elif age < timedelta(days=4 * 365):
            score += 10
        elif age < timedelta(days=6 * 365):
            score += 5

    # 4. Read-on history breadth
    read_on_count = len(c.read_on_history)
    if read_on_count >= 5:
        score += 10
    elif read_on_count >= 3:
        score += 7
    elif read_on_count >= 1:
        score += 4

    # 5. Citizenship
    if c.citizenship == Citizenship.US_CITIZEN.value:
        score += 10
    elif c.citizenship == Citizenship.PERMANENT_RESIDENT.value:
        score += 4

    # 6. ITAR/EAR eligibility
    if c.itar_ear_eligible:
        score += 5

    # 7. Availability
    avail_points = {
        AvailabilityWindow.IMMEDIATELY.value: 5,
        AvailabilityWindow.TWO_WEEKS.value: 4,
        AvailabilityWindow.THIRTY_DAYS.value: 2,
        AvailabilityWindow.NOT_LOOKING.value: 0,
    }
    if c.engagement.availability_window:
        score += avail_points.get(c.engagement.availability_window, 0)

    return min(100, max(0, score))
