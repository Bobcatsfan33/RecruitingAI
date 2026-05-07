"""Cleared talent supply heat maps.

Aggregates the candidates DB by clearance × geography × LCAT/skill into
a sparse heat-map structure the dashboard can render. Pure function over
a (caller-supplied) iterable of candidate facets so this file has zero
DB dependency and is easy to test.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass
class HeatmapCell:
    clearance: str
    metro: str
    lcat_or_skill: str
    count: int
    available_now_count: int


@dataclass
class CandidateFacet:
    clearance: str
    metro: str
    lcat_or_skill: str
    available_now: bool


def build(facets: Iterable[CandidateFacet]) -> list[HeatmapCell]:
    cells: dict[tuple[str, str, str], HeatmapCell] = {}
    for facet in facets:
        key = (facet.clearance, facet.metro, facet.lcat_or_skill)
        cell = cells.get(key)
        if cell is None:
            cell = HeatmapCell(
                clearance=facet.clearance,
                metro=facet.metro,
                lcat_or_skill=facet.lcat_or_skill,
                count=0,
                available_now_count=0,
            )
            cells[key] = cell
        cell.count += 1
        if facet.available_now:
            cell.available_now_count += 1
    out = list(cells.values())
    out.sort(key=lambda c: (-c.count, c.clearance, c.metro))
    return out


def summarise_by_clearance(cells: list[HeatmapCell]) -> dict[str, dict[str, int]]:
    """Two-axis summary: clearance × metro -> count."""
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for cell in cells:
        out[cell.clearance][cell.metro] += cell.count
    return {k: dict(v) for k, v in out.items()}
