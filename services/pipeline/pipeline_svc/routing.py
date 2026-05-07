"""Multi-req routing.

When a candidate is screened against Req A and ends disqualified-but-
promising, we re-evaluate them against every other active req for which
they could plausibly fit. The router uses the candidate's profile
embedding + structured filters (clearance floor, motion, metro) to find
plausible reqs from the requisitions table; the actual screen happens
out-of-process by enqueueing one screening job per match.

Pure function — caller supplies the active reqs + candidate vector and
gets back a ranked match list.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID


@dataclass
class ReqMatch:
    requisition_id: UUID
    score: float          # cosine similarity
    matches_clearance: bool
    matches_motion: bool
    matches_metro: bool


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class CandidateView:
    embedding: list[float]
    clearance: str
    motion: str | None
    metro: str | None


@dataclass
class RequisitionView:
    id: UUID
    embedding: list[float]
    clearance_minimum: str
    motion_required: str | None
    metro: str | None


_CLEARANCE_RANK = {
    "none": 0, "public_trust": 1, "secret": 2, "top_secret": 3, "ts_sci": 4,
}


def route(
    candidate: CandidateView,
    reqs: Iterable[RequisitionView],
    *,
    score_floor: float = 0.65,
    limit: int = 10,
) -> list[ReqMatch]:
    matches: list[ReqMatch] = []
    cand_clearance_rank = _CLEARANCE_RANK.get(candidate.clearance, 0)
    for req in reqs:
        score = _cosine(candidate.embedding, req.embedding)
        clearance_ok = cand_clearance_rank >= _CLEARANCE_RANK.get(req.clearance_minimum, 0)
        if not clearance_ok:
            continue
        motion_ok = (req.motion_required is None) or (candidate.motion == req.motion_required)
        metro_ok = (req.metro is None) or (candidate.metro == req.metro)
        # A vacuously-true motion/metro filter (because the req didn't specify
        # one) shouldn't rescue a candidate whose embedding is far away.
        # Only an explicit positive match counts as a strong signal.
        explicit_motion_match = req.motion_required is not None and candidate.motion == req.motion_required
        explicit_metro_match = req.metro is not None and candidate.metro == req.metro
        strong_signal = explicit_motion_match and explicit_metro_match
        if score < score_floor and not strong_signal:
            continue
        matches.append(
            ReqMatch(
                requisition_id=req.id,
                score=round(score, 4),
                matches_clearance=clearance_ok,
                matches_motion=motion_ok,
                matches_metro=metro_ok,
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:limit]
