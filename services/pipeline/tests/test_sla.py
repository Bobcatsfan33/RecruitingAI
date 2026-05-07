"""SLA / stage health tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pipeline_svc.sla import evaluate, overall_pipeline_velocity
from pipeline_svc.state import Stage


def test_recent_entry_is_ok():
    h = evaluate(Stage.SCREENING, datetime.now(timezone.utc) - timedelta(hours=2))
    assert h.breach_severity == "ok"
    assert not h.sla_breach


def test_warning_at_75_percent_of_budget():
    # Screening budget = 3 days; warn at 2.25 days.
    h = evaluate(Stage.SCREENING, datetime.now(timezone.utc) - timedelta(days=2, hours=12))
    assert h.breach_severity == "warning"
    assert not h.sla_breach


def test_breach_at_full_budget():
    h = evaluate(Stage.SCREENING, datetime.now(timezone.utc) - timedelta(days=4))
    assert h.breach_severity == "breached"
    assert h.sla_breach


def test_overall_pipeline_velocity_counts_transitions():
    events = [
        {"stage_from": "screening", "stage_to": "outreach", "occurred_at": "x"},
        {"stage_from": "screening", "stage_to": "outreach", "occurred_at": "y"},
        {"stage_from": "outreach", "stage_to": "interview", "occurred_at": "z"},
    ]
    out = overall_pipeline_velocity(events)
    assert out["screening->outreach"] == 2
    assert out["outreach->interview"] == 1
