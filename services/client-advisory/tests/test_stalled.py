"""Stalled-pipeline diagnosis tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from client_advisory_svc.stalled import diagnose


def test_no_events_returns_neutral_diagnosis():
    out = diagnose([])
    assert out.bottleneck_stage is None
    assert "no pipeline activity" in out.likely_causes[0]


def test_outreach_bottleneck_recognized():
    now = datetime.now(timezone.utc)
    events = [
        {"stage_to": "outreach", "occurred_at": (now - timedelta(days=14)).isoformat()},
        {"stage_to": "outreach", "occurred_at": (now - timedelta(days=10)).isoformat()},
        {"stage_to": "outreach", "occurred_at": (now - timedelta(days=8)).isoformat()},
        {"stage_to": "screening", "occurred_at": (now - timedelta(days=20)).isoformat()},
    ]
    out = diagnose(events)
    assert out.bottleneck_stage == "outreach"


def test_low_conversion_drop_off_flagged():
    now = datetime.now(timezone.utc)
    events = []
    # 10 candidates entered screening, only 2 made it to outreach.
    for _ in range(10):
        events.append({
            "stage_from": "sourcing",
            "stage_to": "screening",
            "occurred_at": now.isoformat(),
        })
    for _ in range(2):
        events.append({
            "stage_from": "screening",
            "stage_to": "outreach",
            "occurred_at": now.isoformat(),
        })
    out = diagnose(events)
    assert out.drop_off_stage == "screening"
    assert out.drop_off_ratio is not None
    assert out.drop_off_ratio < 0.3
