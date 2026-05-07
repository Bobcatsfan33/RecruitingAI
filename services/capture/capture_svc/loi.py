"""Letter-of-Intent workflow.

Pre-award capture — we identify candidates, secure contingent commitments
(LOI), and bundle the documentation into the proposal package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class LoiStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    SIGNED = "signed"
    DECLINED = "declined"
    EXPIRED = "expired"


@dataclass
class Loi:
    id: UUID
    candidate_id: UUID
    opportunity_name: str
    contract_vehicle: str
    lcat_code: str
    period_of_performance_start: date
    period_of_performance_end: date
    contingent_offer_summary: str
    status: LoiStatus = LoiStatus.DRAFT
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=90)
    )
    signed_at: datetime | None = None
    document_url: str | None = None


@dataclass
class LoiPackage:
    opportunity_name: str
    contract_vehicle: str
    submitted_at: datetime
    lois: list[Loi]

    def acceptance_rate(self) -> float:
        if not self.lois:
            return 0.0
        signed = sum(1 for l in self.lois if l.status == LoiStatus.SIGNED)
        return signed / len(self.lois)


def draft_loi(
    *,
    candidate_id: UUID,
    opportunity_name: str,
    contract_vehicle: str,
    lcat_code: str,
    period_of_performance_start: date,
    period_of_performance_end: date,
    proposed_salary: int | None = None,
    proposed_bill_rate: float | None = None,
    notes: str = "",
) -> Loi:
    summary_lines = [
        f"Opportunity: {opportunity_name}",
        f"Vehicle: {contract_vehicle}, LCAT: {lcat_code}",
        f"Period of performance: {period_of_performance_start} → {period_of_performance_end}",
    ]
    if proposed_salary:
        summary_lines.append(f"Proposed annual salary: ${proposed_salary:,}")
    if proposed_bill_rate:
        summary_lines.append(f"Proposed bill rate: ${proposed_bill_rate:.2f}/hr")
    if notes:
        summary_lines.append(f"Notes: {notes}")
    return Loi(
        id=uuid4(),
        candidate_id=candidate_id,
        opportunity_name=opportunity_name,
        contract_vehicle=contract_vehicle,
        lcat_code=lcat_code,
        period_of_performance_start=period_of_performance_start,
        period_of_performance_end=period_of_performance_end,
        contingent_offer_summary="\n".join(summary_lines),
    )


def package(
    opportunity_name: str,
    contract_vehicle: str,
    lois: list[Loi],
) -> LoiPackage:
    return LoiPackage(
        opportunity_name=opportunity_name,
        contract_vehicle=contract_vehicle,
        submitted_at=datetime.now(timezone.utc),
        lois=lois,
    )


def expired(loi: Loi, *, now: datetime | None = None) -> bool:
    return (now or datetime.now(timezone.utc)) > loi.expires_at
