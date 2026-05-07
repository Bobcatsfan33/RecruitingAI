"""Compensation benchmarking from verified candidate interaction data.

Inputs: list of CompPoint records (one per W-2 verified interaction the
platform observed). Returns percentile bands (p25/p50/p75/p90) per role
× location × clearance segment.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class CompPoint:
    role_type: str
    seniority: str  # junior | mid | senior | sme
    location: str
    clearance: str
    ote: float
    base: float | None = None
    w2_verified: bool = False
    year: int | None = None


@dataclass
class CompBenchmark:
    role_type: str
    seniority: str
    location: str
    clearance: str
    sample_size: int
    p25: float
    p50: float
    p75: float
    p90: float
    mean: float
    stddev: float


def benchmarks(points: list[CompPoint], *, w2_only: bool = True) -> list[CompBenchmark]:
    if w2_only:
        points = [p for p in points if p.w2_verified]
    bucket: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    for p in points:
        key = (p.role_type, p.seniority, p.location, p.clearance)
        bucket[key].append(float(p.ote))
    out: list[CompBenchmark] = []
    for (role, seniority, location, clearance), values in bucket.items():
        if len(values) < 3:
            continue  # sample too small to report
        values.sort()
        out.append(CompBenchmark(
            role_type=role, seniority=seniority, location=location, clearance=clearance,
            sample_size=len(values),
            p25=_percentile(values, 0.25),
            p50=_percentile(values, 0.50),
            p75=_percentile(values, 0.75),
            p90=_percentile(values, 0.90),
            mean=round(statistics.fmean(values), 2),
            stddev=round(statistics.pstdev(values), 2) if len(values) > 1 else 0.0,
        ))
    out.sort(key=lambda b: (b.role_type, b.seniority, b.location, b.clearance))
    return out


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return round(sorted_values[0], 2)
    rank = p * (len(sorted_values) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return round(sorted_values[lo], 2)
    weight = rank - lo
    return round(sorted_values[lo] * (1 - weight) + sorted_values[hi] * weight, 2)
