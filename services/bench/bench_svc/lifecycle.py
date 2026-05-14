"""Contractor lifecycle — contract end alerts, clearance expiration tracking,
redeployment status."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from uuid import UUID


class AlertSeverity(str, Enum):
    INFO = "info"
    WATCH = "watch"
    URGENT = "urgent"


class AlertType(str, Enum):
    CONTRACT_END_T_MINUS_90 = "contract_end_t_minus_90"
    CONTRACT_END_T_MINUS_60 = "contract_end_t_minus_60"
    CONTRACT_END_T_MINUS_30 = "contract_end_t_minus_30"
    CLEARANCE_EXPIRY_T_MINUS_180 = "clearance_expiry_t_minus_180"
    CLEARANCE_EXPIRY_T_MINUS_90 = "clearance_expiry_t_minus_90"
    CLEARANCE_EXPIRY_T_MINUS_30 = "clearance_expiry_t_minus_30"


@dataclass
class BenchAlert:
    candidate_id: UUID
    contract_id: UUID | None
    type: AlertType
    severity: AlertSeverity
    target_date: date
    days_remaining: int
    message: str


@dataclass
class ContractorRecord:
    candidate_id: UUID
    contract_id: UUID | None
    contract_end_date: date | None
    clearance_expiry_date: date | None
    last_clearance_renewal: date | None = None
    voluntary: bool = True


def _today() -> date:
    return datetime.now(UTC).date()


def evaluate_contractor(
    record: ContractorRecord, *, today: date | None = None,
) -> list[BenchAlert]:
    today = today or _today()
    alerts: list[BenchAlert] = []
    if record.contract_end_date:
        days = (record.contract_end_date - today).days
        if 0 <= days <= 30:
            alerts.append(BenchAlert(
                candidate_id=record.candidate_id, contract_id=record.contract_id,
                type=AlertType.CONTRACT_END_T_MINUS_30, severity=AlertSeverity.URGENT,
                target_date=record.contract_end_date, days_remaining=days,
                message=f"Contract ends in {days} days — redeploy or convert NOW.",
            ))
        elif 30 < days <= 60:
            alerts.append(BenchAlert(
                candidate_id=record.candidate_id, contract_id=record.contract_id,
                type=AlertType.CONTRACT_END_T_MINUS_60, severity=AlertSeverity.WATCH,
                target_date=record.contract_end_date, days_remaining=days,
                message=f"Contract ends in {days} days — surface redeployment options.",
            ))
        elif 60 < days <= 90:
            alerts.append(BenchAlert(
                candidate_id=record.candidate_id, contract_id=record.contract_id,
                type=AlertType.CONTRACT_END_T_MINUS_90, severity=AlertSeverity.INFO,
                target_date=record.contract_end_date, days_remaining=days,
                message=f"Contract ends in {days} days.",
            ))

    if record.clearance_expiry_date:
        days = (record.clearance_expiry_date - today).days
        if 0 <= days <= 30:
            alerts.append(BenchAlert(
                candidate_id=record.candidate_id, contract_id=record.contract_id,
                type=AlertType.CLEARANCE_EXPIRY_T_MINUS_30, severity=AlertSeverity.URGENT,
                target_date=record.clearance_expiry_date, days_remaining=days,
                message=f"Clearance expires in {days} days — initiate renewal NOW.",
            ))
        elif 30 < days <= 90:
            alerts.append(BenchAlert(
                candidate_id=record.candidate_id, contract_id=record.contract_id,
                type=AlertType.CLEARANCE_EXPIRY_T_MINUS_90, severity=AlertSeverity.WATCH,
                target_date=record.clearance_expiry_date, days_remaining=days,
                message=f"Clearance expires in {days} days.",
            ))
        elif 90 < days <= 180:
            alerts.append(BenchAlert(
                candidate_id=record.candidate_id, contract_id=record.contract_id,
                type=AlertType.CLEARANCE_EXPIRY_T_MINUS_180, severity=AlertSeverity.INFO,
                target_date=record.clearance_expiry_date, days_remaining=days,
                message=f"Clearance expires in {days} days.",
            ))
    return alerts


def evaluate_bench(
    records: Iterable[ContractorRecord], *, today: date | None = None,
) -> list[BenchAlert]:
    today = today or _today()
    out: list[BenchAlert] = []
    for record in records:
        out.extend(evaluate_contractor(record, today=today))
    out.sort(key=lambda a: a.days_remaining)
    return out
