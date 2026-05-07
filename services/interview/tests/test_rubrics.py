"""Rubric library sanity."""

from __future__ import annotations

from interview_svc.rubrics import RUBRICS, for_role


def test_three_baseline_rubrics():
    assert set(RUBRICS) == {"sales", "sales_engineering", "cleared"}


def test_unknown_role_falls_back_to_sales():
    assert for_role("nonexistent").role_type == "sales"


def test_each_rubric_has_dimensions():
    for rubric in RUBRICS.values():
        assert len(rubric.dimensions) >= 4
        assert all(d.weight > 0 for d in rubric.dimensions)


def test_quota_validation_dimension_in_sales():
    sales = RUBRICS["sales"]
    keys = {d.name for d in sales.dimensions}
    assert "quota_validation" in keys


def test_clearance_timeline_dimension_in_cleared():
    cleared = RUBRICS["cleared"]
    keys = {d.name for d in cleared.dimensions}
    assert "clearance_timeline" in keys
