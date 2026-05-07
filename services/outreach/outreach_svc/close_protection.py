"""Close Protection agent.

Activated on offer acceptance. Drives the post-acceptance cadence and
watches for falloff signals (counteroffer, cooling, no-show). When falloff
is detected we:
1. Audit-log the event.
2. Emit a `candidate_falloff` interaction event so the Pipeline Manager
   (Sprint 5) can promote a silver medalist within the 48h SLA.
3. Mark the close-protection sequence as terminated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import structlog

from outreach_svc.classifier import ClassificationResult, classify
from outreach_svc.sequences import (
    CLOSE_PROTECTION,
    StepInstance,
    StepStatus,
    materialise,
    next_step,
    stop_on_response,
)
from wfi_audit import AuditLogger, NullAuditLogger
from wfi_events import EventPublisher, NullEventPublisher
from wfi_llm import ModelRouter, NullModelRouter
from wfi_schemas import (
    ActionType,
    AgentType,
    AuditLogEntry,
    EventType,
    InteractionEvent,
    Outcome,
)

log = structlog.get_logger("outreach.close_protection")


class CloseProtectionAgent:
    def __init__(
        self,
        *,
        audit: AuditLogger | NullAuditLogger,
        events: EventPublisher | NullEventPublisher,
        router: ModelRouter | NullModelRouter | None = None,
    ) -> None:
        self._audit = audit
        self._events = events
        self._router = router

    def activate(self, *, started_at: datetime | None = None) -> list[StepInstance]:
        return materialise(CLOSE_PROTECTION, started_at=started_at or datetime.now(timezone.utc))

    def next_send(self, instances: list[StepInstance]) -> StepInstance | None:
        return next_step(instances)

    async def handle_response(
        self,
        instances: list[StepInstance],
        *,
        candidate_id: UUID,
        requisition_id: UUID | None,
        reply_text: str,
    ) -> dict:
        result: ClassificationResult = await classify(reply_text, router=self._router)
        log.info(
            "close_protection_response",
            candidate_id=str(candidate_id),
            label=result.label,
            confidence=result.confidence,
        )

        outcome: Outcome
        falloff = False
        if result.label == "counteroffer_signal":
            outcome = Outcome.NEGATIVE
            falloff = True
        elif result.label in ("not_interested",):
            outcome = Outcome.NEGATIVE
            falloff = True
        elif result.label == "interested":
            outcome = Outcome.POSITIVE
        else:
            outcome = Outcome.NEUTRAL

        await self._events.publish(
            InteractionEvent(
                event_type=EventType.OUTREACH_REPLIED,
                candidate_id=candidate_id,
                requisition_id=requisition_id,
                agent_type=AgentType.CLOSE_PROTECTION,
                channel=None,
                metadata={
                    "label": result.label,
                    "confidence": result.confidence,
                    "method": result.method,
                    "reasoning": result.reasoning,
                },
                outcome=outcome,
            )
        )

        if falloff:
            await self._events.publish(
                InteractionEvent(
                    event_type=EventType.CANDIDATE_FALLOFF,
                    candidate_id=candidate_id,
                    requisition_id=requisition_id,
                    agent_type=AgentType.CLOSE_PROTECTION,
                    metadata={"reason": result.label},
                    outcome=Outcome.NEGATIVE,
                )
            )
            await self._audit.record(
                AuditLogEntry(
                    action_type=ActionType.ESCALATION_TRIGGERED,
                    candidate_id=candidate_id,
                    requisition_id=requisition_id,
                    agent_type="close_protection",
                    model_used=result.method,
                    decision="falloff_detected",
                    reasoning=f"label={result.label} confidence={result.confidence:.2f}",
                    confidence_score=result.confidence,
                )
            )
            stop_on_response(instances, "not_interested")

        # Update the most recent sent step (or last) with response.
        for inst in reversed(instances):
            if inst.status == StepStatus.SENT:
                inst.response = result.label
                break

        return {
            "label": result.label,
            "confidence": result.confidence,
            "method": result.method,
            "falloff": falloff,
        }
