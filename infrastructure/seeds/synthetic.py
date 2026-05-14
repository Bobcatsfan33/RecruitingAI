"""Generate synthetic but realistic candidates + requisitions for dev.

We have no real placements (per the build constraint) so dev work runs
against this synthetic corpus. Reproducible via seed.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from datetime import date, timedelta

from wfi_schemas import (
    AvailabilityWindow,
    Candidate,
    CandidateSource,
    CareerHistoryEntry,
    Citizenship,
    ClearanceStatus,
    ClearanceType,
    CompType,
    EngagementSignals,
    PolygraphType,
    PreferredChannel,
    ReqType,
    Requisition,
    SalesMotion,
)

CLEARED_METROS = ["DC Metro", "Tampa Bay", "Huntsville", "San Antonio", "Colorado Springs"]
COMMERCIAL_METROS = ["SF Bay Area", "Austin", "Boston", "Seattle", "NYC Metro", "Denver"]

CLEARED_TITLES = [
    "Cleared Sales Engineer",
    "DOD Account Executive",
    "Federal Solutions Architect",
    "Cleared Cyber Engineer",
    "TS/SCI Software Engineer",
    "Federal Channel Manager",
]
COMMERCIAL_TITLES = [
    "Enterprise Account Executive",
    "Senior Sales Engineer",
    "Director of Strategic Accounts",
    "Mid-Market AE",
    "Solutions Architect",
    "Head of GTM",
]

FIRST_NAMES = [
    "Avery", "Jordan", "Morgan", "Riley", "Cameron", "Quinn", "Taylor",
    "Kai", "Devon", "Hayden", "Reese", "Skyler", "Drew", "Sasha", "Phoenix",
]
LAST_NAMES = [
    "Patel", "Nguyen", "Walker", "Bennett", "Hayes", "Ramirez", "Yamamoto",
    "Okonkwo", "Sutherland", "Lindqvist", "Martinez", "Brown", "Cohen",
]


def _rand_phone(rng: random.Random) -> str:
    return f"+1555{rng.randint(2000000, 9999999)}"


def synthetic_candidates(seed: int = 42, count: int = 500) -> Iterator[Candidate]:
    rng = random.Random(seed)
    for i in range(count):
        cleared = rng.random() < 0.5
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        domain = rng.choice(["mock.local", "example.com", "synth.dev"])
        email = f"{first.lower()}.{last.lower()}.{i}@{domain}"
        metros = CLEARED_METROS if cleared else COMMERCIAL_METROS
        metro = rng.choice(metros)
        clearance = (
            rng.choice([ClearanceType.SECRET, ClearanceType.TOP_SECRET, ClearanceType.TS_SCI])
            if cleared
            else ClearanceType.NONE
        )
        poly = (
            rng.choice([PolygraphType.NONE, PolygraphType.CI, PolygraphType.FULL_SCOPE])
            if clearance == ClearanceType.TS_SCI
            else PolygraphType.NONE
        )
        title_pool = CLEARED_TITLES if cleared else COMMERCIAL_TITLES
        career: list[CareerHistoryEntry] = []
        years = rng.randint(4, 18)
        end = date.today()
        for j in range(rng.randint(2, 5)):
            stint_years = rng.randint(1, 5)
            start = end - timedelta(days=stint_years * 365)
            career.append(
                CareerHistoryEntry(
                    company=rng.choice(
                        ["Booz Allen", "Leidos", "CACI", "Snowflake", "Datadog", "Okta",
                         "Palantir", "MongoDB", "GitLab", "Cloudflare", "Splunk", "ManTech"]
                    ),
                    title=rng.choice(title_pool),
                    start_date=start,
                    end_date=None if j == 0 else end,
                )
            )
            end = start - timedelta(days=30)

        yield Candidate(
            source=CandidateSource.MANUAL,
            first_name=first,
            last_name=last,
            email=email,
            phone=_rand_phone(rng),
            location_metro=metro,
            location_state=rng.choice(["VA", "MD", "TX", "FL", "CO", "CA", "NY", "WA"]),
            citizenship=Citizenship.US_CITIZEN if cleared else Citizenship.PERMANENT_RESIDENT,
            clearance_type=clearance,
            polygraph=poly,
            clearance_status=ClearanceStatus.ACTIVE if cleared else None,
            adjudication_date=date.today() - timedelta(days=rng.randint(60, 5 * 365))
            if cleared else None,
            primary_motion=rng.choice(list(SalesMotion)),
            career_history=career,
            tags=["sales"] + (["cleared"] if cleared else []),
            engagement=EngagementSignals(
                preferred_channel=rng.choice(list(PreferredChannel)),
                approachability_score=rng.randint(20, 95),
                availability_window=rng.choice(list(AvailabilityWindow)),
            ),
        )
        del years  # silence linter — value used only via the loop above


def synthetic_requisitions(seed: int = 7, count: int = 25) -> Iterator[Requisition]:
    rng = random.Random(seed)
    from uuid import uuid4

    client_id = uuid4()  # caller substitutes a real client_id
    for _ in range(count):
        cleared = rng.random() < 0.5
        yield Requisition(
            client_id=client_id,
            req_type=rng.choice(list(ReqType)),
            title=rng.choice(CLEARED_TITLES if cleared else COMMERCIAL_TITLES),
            comp_type=CompType.SALARY,
            budget_min=rng.choice([180_000, 220_000, 260_000]),
            budget_max=rng.choice([280_000, 320_000, 380_000]),
            clearance_minimum=ClearanceType.TS_SCI if cleared else ClearanceType.NONE,
            polygraph_required=PolygraphType.CI if cleared and rng.random() < 0.4 else PolygraphType.NONE,
            must_have_skills=rng.sample(
                ["MEDDIC", "Challenger", "Force Management", "Snowflake", "MongoDB",
                 "Cyber", "Cloud", "AI/ML", "Federal", "Networking"],
                k=rng.randint(2, 5),
            ),
        )
