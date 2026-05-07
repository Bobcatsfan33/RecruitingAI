"""Sequence engine.

A sequence is a list of `Step`s; each step has a channel, template,
relative offset (days/hours), and optional branching (`continue_if`).
The engine returns the next step that should fire NOW given the
candidate's state and history.

Two pre-baked sequences:
- `precision_outreach`: 5 touches over 14 days, email-heavy with personalisation hooks.
- `velocity_outreach`: 3 touches in 5 days, phone+text priority.
- `close_protection`: post-acceptance high-touch through notice period.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class StepStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    SKIPPED = "skipped"


@dataclass
class Step:
    key: str
    channel: str          # email | sms | linkedin | phone
    template_id: str
    offset_hours: int     # hours from sequence start
    branch_when: dict[str, str] | None = None  # response_class -> next_template_id
    inoculate_counteroffer: bool = False


@dataclass
class StepInstance:
    step: Step
    fire_at: datetime
    status: StepStatus = StepStatus.PENDING
    sent_at: datetime | None = None
    response: str | None = None  # interested|not_now|not_interested|wrong_fit
    skipped_reason: str | None = None


@dataclass
class Sequence:
    key: str
    steps: list[Step] = field(default_factory=list)


PRECISION_OUTREACH = Sequence(
    key="precision_outreach",
    steps=[
        Step("intro_email", "email", "intro_v1", offset_hours=0),
        Step("li_followup", "linkedin", "li_intro_v1", offset_hours=24),
        Step("value_email", "email", "value_v1", offset_hours=72,
             inoculate_counteroffer=True),
        Step("touch3_email", "email", "touch3_v1", offset_hours=24 * 7),
        Step("breakup", "email", "breakup_v1", offset_hours=24 * 14),
    ],
)


VELOCITY_OUTREACH = Sequence(
    key="velocity_outreach",
    steps=[
        Step("text_intro", "sms", "velocity_text_v1", offset_hours=0),
        Step("phone_followup", "phone", "velocity_call_v1", offset_hours=4),
        Step("email_recap", "email", "velocity_recap_v1", offset_hours=24),
    ],
)


CLOSE_PROTECTION = Sequence(
    key="close_protection",
    steps=[
        Step("day1_celebrate", "email", "cp_day1_v1", offset_hours=24),
        Step("day3_logistics", "email", "cp_day3_v1", offset_hours=72),
        Step("day7_checkin", "sms", "cp_day7_v1", offset_hours=168),
        Step("day10_recap", "email", "cp_day10_v1", offset_hours=240),
        Step("day14_recap", "email", "cp_day14_v1", offset_hours=336),
        Step("day21_recap", "email", "cp_day21_v1", offset_hours=504),
        Step("day28_recap", "sms", "cp_day28_v1", offset_hours=672),
    ],
)

SEQUENCES: dict[str, Sequence] = {
    s.key: s for s in (PRECISION_OUTREACH, VELOCITY_OUTREACH, CLOSE_PROTECTION)
}


def materialise(sequence: Sequence, *, started_at: datetime | None = None) -> list[StepInstance]:
    started_at = started_at or datetime.now(timezone.utc)
    return [
        StepInstance(step=step, fire_at=started_at + timedelta(hours=step.offset_hours))
        for step in sequence.steps
    ]


def next_step(instances: list[StepInstance], *, now: datetime | None = None) -> StepInstance | None:
    """Return the earliest pending step whose fire_at has elapsed."""
    now = now or datetime.now(timezone.utc)
    candidates = [
        i for i in instances
        if i.status == StepStatus.PENDING and i.fire_at <= now
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda i: i.fire_at)
    return candidates[0]


def stop_on_response(
    instances: list[StepInstance],
    response_class: str,
) -> list[StepInstance]:
    """Mark all remaining pending steps as skipped after a terminal response."""
    terminal = {"interested", "not_interested", "wrong_fit"}
    if response_class not in terminal:
        return instances
    for inst in instances:
        if inst.status == StepStatus.PENDING:
            inst.status = StepStatus.SKIPPED
            inst.skipped_reason = f"response={response_class}"
    return instances
