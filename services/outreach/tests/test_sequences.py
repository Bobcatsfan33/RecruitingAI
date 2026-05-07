"""Sequence engine tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from outreach_svc.sequences import (
    CLOSE_PROTECTION,
    PRECISION_OUTREACH,
    StepStatus,
    materialise,
    next_step,
    stop_on_response,
)


def test_materialise_sets_fire_at_relative_to_start():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    instances = materialise(PRECISION_OUTREACH, started_at=start)
    assert instances[0].fire_at == start
    assert instances[1].fire_at == start + timedelta(hours=24)
    assert instances[-1].fire_at == start + timedelta(hours=24 * 14)


def test_next_step_returns_earliest_pending_due():
    start = datetime.now(timezone.utc) - timedelta(hours=80)
    instances = materialise(PRECISION_OUTREACH, started_at=start)
    instances[0].status = StepStatus.SENT
    nxt = next_step(instances)
    assert nxt is not None
    assert nxt.step.key in {"li_followup", "value_email"}


def test_next_step_returns_none_when_nothing_due():
    start = datetime.now(timezone.utc)
    instances = materialise(PRECISION_OUTREACH, started_at=start)
    instances[0].status = StepStatus.SENT
    assert next_step(instances) is None


def test_stop_on_response_skips_remaining():
    instances = materialise(PRECISION_OUTREACH)
    instances[0].status = StepStatus.SENT
    stop_on_response(instances, "not_interested")
    assert all(i.status in {StepStatus.SENT, StepStatus.SKIPPED} for i in instances)


def test_stop_on_response_does_nothing_for_non_terminal():
    instances = materialise(PRECISION_OUTREACH)
    pending_before = sum(1 for i in instances if i.status == StepStatus.PENDING)
    stop_on_response(instances, "ooo")
    pending_after = sum(1 for i in instances if i.status == StepStatus.PENDING)
    assert pending_before == pending_after


def test_close_protection_has_seven_steps():
    instances = materialise(CLOSE_PROTECTION)
    assert len(instances) == 7
    keys = [i.step.key for i in instances]
    assert keys[0] == "day1_celebrate"
    assert keys[-1] == "day28_recap"
