"""Predicate evaluator tests."""

from __future__ import annotations

from screening_svc.predicates import evaluate

CANDIDATE = {
    "first_name": "Sam",
    "last_name": "Lee",
    "primary_motion": "enterprise",
    "clearance_type": "ts_sci",
    "career_history": [
        {"company": "Acme", "title": "Senior AE", "start_date": "2022-01-01"},
        {"company": "Beta", "title": "AE"},
    ],
    "compensation_history": [
        {"base": 200000, "ote": 380000, "year": 2024},
    ],
    "tags": ["sales", "cleared"],
    "se_demo_skill_rating": 4,
}


def test_field_eq():
    assert evaluate("field_eq:primary_motion=enterprise", CANDIDATE) is True
    assert evaluate("field_eq:primary_motion=plg", CANDIDATE) is False


def test_field_neq():
    assert evaluate("field_neq:clearance_type=none", CANDIDATE) is True


def test_field_in():
    assert evaluate("field_in:primary_motion in [enterprise, mid_market]", CANDIDATE) is True
    assert evaluate("field_in:primary_motion in [smb_velocity, plg]", CANDIDATE) is False


def test_field_in_works_for_array_values():
    assert evaluate("field_in:tags in [cleared, federal]", CANDIDATE) is True


def test_field_gte_lte():
    assert evaluate("field_gte:se_demo_skill_rating>=4", CANDIDATE) is True
    assert evaluate("field_gte:se_demo_skill_rating>=5", CANDIDATE) is False
    assert evaluate("field_lte:se_demo_skill_rating<=4", CANDIDATE) is True


def test_field_present_and_truthy():
    assert evaluate("field_present:first_name", CANDIDATE) is True
    assert evaluate("field_present:nonexistent", CANDIDATE) is False
    assert evaluate("field_truthy:tags", CANDIDATE) is True


def test_nested_path_through_array():
    assert evaluate("field_eq:career_history.0.company=Acme", CANDIDATE) is True


def test_llm_predicate_returns_none():
    assert evaluate("llm:role_fit", CANDIDATE) is None


def test_unknown_predicate_returns_none():
    assert evaluate("nonsense:foo=bar", CANDIDATE) is None
