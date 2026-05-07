"""Escalation triggers."""

from __future__ import annotations

from screening_svc.escalation import detect
from wfi_schemas import EscalationFlag


def _candidate(**overrides):
    base = {
        "career_history": [{"title": "Senior Account Executive", "company": "Datadog"}],
        "compensation_history": [{"ote": 180000, "year": 2024}],
    }
    base.update(overrides)
    return base


def test_vp_plus_title_triggers():
    flags = detect(_candidate(career_history=[{"title": "VP of Sales", "company": "X"}]))
    assert EscalationFlag.VP_PLUS in flags


def test_chief_title_triggers():
    flags = detect(_candidate(career_history=[{"title": "Chief Revenue Officer", "company": "X"}]))
    assert EscalationFlag.VP_PLUS in flags


def test_high_comp_triggers():
    flags = detect(_candidate(compensation_history=[{"ote": 420000, "year": 2024}]))
    assert EscalationFlag.HIGH_COMP in flags


def test_normal_candidate_no_flags():
    flags = detect(_candidate())
    assert flags == []


def test_active_non_compete_triggers():
    flags = detect(_candidate(), ownership_status={"has_non_compete": True})
    assert EscalationFlag.ACTIVE_NON_COMPETE in flags


def test_ownership_blocked_triggers():
    flags = detect(_candidate(), ownership_status={"is_dnc": True})
    assert EscalationFlag.OWNERSHIP_BLOCKED in flags


def test_mixed_signals_when_split_pass_fail():
    crits = [
        {"passed": True}, {"passed": True}, {"passed": False}, {"passed": False},
    ]
    flags = detect(_candidate(), criterion_results=crits)
    assert EscalationFlag.MIXED_SIGNALS in flags


def test_no_mixed_signals_when_clear_pass():
    crits = [{"passed": True} for _ in range(5)]
    flags = detect(_candidate(), criterion_results=crits)
    assert EscalationFlag.MIXED_SIGNALS not in flags
