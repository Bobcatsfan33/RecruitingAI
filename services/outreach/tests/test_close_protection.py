"""Close Protection agent end-to-end."""

from __future__ import annotations

from uuid import uuid4

import pytest

from outreach_svc.close_protection import CloseProtectionAgent
from outreach_svc.sequences import StepStatus
from wfi_audit import NullAuditLogger
from wfi_events import NullEventPublisher
from wfi_llm import NullModelRouter


def _agent() -> CloseProtectionAgent:
    return CloseProtectionAgent(
        audit=NullAuditLogger(),
        events=NullEventPublisher(),
        router=NullModelRouter(response_text='{"label": "interested", "confidence": 0.6}'),
    )


def test_activation_creates_seven_steps():
    agent = _agent()
    instances = agent.activate()
    assert len(instances) == 7
    assert all(i.status == StepStatus.PENDING for i in instances)


@pytest.mark.asyncio
async def test_counteroffer_signal_triggers_falloff():
    agent = _agent()
    audit: NullAuditLogger = agent._audit
    events: NullEventPublisher = agent._events
    instances = agent.activate()
    instances[0].status = StepStatus.SENT
    out = await agent.handle_response(
        instances,
        candidate_id=uuid4(),
        requisition_id=uuid4(),
        reply_text="My current company is countering with a 20% raise.",
    )
    assert out["falloff"] is True
    assert any(e.event_type == "candidate_falloff" for e in events.events)
    assert any(e.action_type == "escalation_triggered" for e in audit.entries)
    # Remaining steps should be skipped after falloff.
    assert all(i.status != StepStatus.PENDING for i in instances)


@pytest.mark.asyncio
async def test_positive_response_does_not_trigger_falloff():
    agent = _agent()
    instances = agent.activate()
    instances[0].status = StepStatus.SENT
    out = await agent.handle_response(
        instances,
        candidate_id=uuid4(),
        requisition_id=uuid4(),
        reply_text="Great, looking forward to starting!",
    )
    assert out["falloff"] is False
    # No skipped steps because not terminal.
    pending_count = sum(1 for i in instances if i.status == StepStatus.PENDING)
    assert pending_count >= 5


@pytest.mark.asyncio
async def test_response_recorded_on_last_sent_step():
    agent = _agent()
    instances = agent.activate()
    instances[0].status = StepStatus.SENT
    instances[1].status = StepStatus.SENT
    await agent.handle_response(
        instances,
        candidate_id=uuid4(),
        requisition_id=None,
        reply_text="Looking forward to it",
    )
    assert instances[1].response is not None
