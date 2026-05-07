"""Bench + compliance tests."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from bench_svc.coemployment import CoEmploymentInputs, summarise
from bench_svc.compliance_adapters import (
    MockBackgroundCheckAdapter,
    MockDissAdapter,
    MockEVerifyAdapter,
)
from bench_svc.conversion import compute, utilisation_rate
from bench_svc.lifecycle import (
    AlertSeverity,
    AlertType,
    ContractorRecord,
    evaluate_bench,
    evaluate_contractor,
)


# --- lifecycle ----------------------------------------------------------

def _record(end_in_days: int | None, clearance_in_days: int | None = None) -> ContractorRecord:
    today = date.today()
    return ContractorRecord(
        candidate_id=uuid4(),
        contract_id=uuid4(),
        contract_end_date=today + timedelta(days=end_in_days) if end_in_days is not None else None,
        clearance_expiry_date=today + timedelta(days=clearance_in_days) if clearance_in_days is not None else None,
    )


def test_t_minus_30_alerts_urgent():
    alerts = evaluate_contractor(_record(end_in_days=15))
    assert any(a.type == AlertType.CONTRACT_END_T_MINUS_30 for a in alerts)
    assert any(a.severity == AlertSeverity.URGENT for a in alerts)


def test_t_minus_60_alerts_watch():
    alerts = evaluate_contractor(_record(end_in_days=45))
    assert any(a.type == AlertType.CONTRACT_END_T_MINUS_60 for a in alerts)


def test_t_minus_90_alerts_info():
    alerts = evaluate_contractor(_record(end_in_days=80))
    assert any(a.type == AlertType.CONTRACT_END_T_MINUS_90 for a in alerts)


def test_no_alerts_when_far_out():
    alerts = evaluate_contractor(_record(end_in_days=200))
    assert all(a.type.name.startswith("CLEARANCE") for a in alerts)  # only clearance, if any


def test_clearance_alerts_layered():
    alerts = evaluate_contractor(_record(end_in_days=200, clearance_in_days=20))
    assert any(a.type == AlertType.CLEARANCE_EXPIRY_T_MINUS_30 for a in alerts)


def test_evaluate_bench_sorts_by_days_remaining():
    records = [_record(end_in_days=120), _record(end_in_days=10), _record(end_in_days=45)]
    alerts = evaluate_bench(records)
    days = [a.days_remaining for a in alerts]
    assert days == sorted(days)


# --- co-employment ------------------------------------------------------

def test_low_risk():
    summary = summarise(CoEmploymentInputs(
        candidate_id="c-1", tenure_months=6, hours_per_week=40,
        supervision_model="vendor_managed",
    ))
    assert summary.risk_band == "low"


def test_medium_risk_aca_threshold():
    summary = summarise(CoEmploymentInputs(
        candidate_id="c-2", tenure_months=20, hours_per_week=30,
        supervision_model="vendor_managed",
    ))
    assert summary.risk_band == "medium"
    assert "tenure>18m" in summary.triggered_thresholds
    assert any("ACA" in t for t in summary.triggered_thresholds)


def test_high_risk_direct_management():
    summary = summarise(CoEmploymentInputs(
        candidate_id="c-3", tenure_months=30, hours_per_week=40,
        supervision_model="direct_client_management",
    ))
    assert summary.risk_band == "high"


# --- conversion fee -----------------------------------------------------

def test_conversion_with_no_credit():
    breakdown = compute(
        hours_worked=200, bill_rate=120.0, first_year_salary=200_000,
        conversion_pct=0.20, credit_per_hour=0.0,
    )
    assert breakdown.base_fee == 40_000.0
    assert breakdown.net_fee == 40_000.0
    assert breakdown.credit == 0.0
    assert not breakdown.waiver_eligible


def test_conversion_with_credit_reduces_fee():
    breakdown = compute(
        hours_worked=500, bill_rate=120.0, first_year_salary=200_000,
        conversion_pct=0.20, credit_per_hour=20.0,
    )
    assert breakdown.credit == 10_000.0
    assert breakdown.net_fee == 30_000.0


def test_waiver_eligible_after_threshold():
    breakdown = compute(
        hours_worked=1500, bill_rate=120.0, first_year_salary=200_000,
        conversion_pct=0.20, credit_per_hour=0.0, waiver_threshold_hours=1000,
    )
    assert breakdown.waiver_eligible


def test_utilisation_rate():
    assert utilisation_rate(bench_hours=20, billable_hours=80) == 0.8
    assert utilisation_rate(bench_hours=0, billable_hours=0) == 0.0


# --- compliance adapters ------------------------------------------------

@pytest.mark.asyncio
async def test_mock_bgc_round_trip():
    bgc = MockBackgroundCheckAdapter()
    initiate = await bgc.initiate(candidate_email="a@b.local")
    assert initiate.success
    status = await bgc.fetch_status(initiate.case_id)
    assert status.status == "completed"


@pytest.mark.asyncio
async def test_mock_diss_returns_active():
    out = await MockDissAdapter().verify(candidate_id="c-1")
    assert out.success
    assert out.clearance_type == "active"


@pytest.mark.asyncio
async def test_mock_everify_returns_authorised():
    out = await MockEVerifyAdapter().submit(
        candidate_email="a@b.local", document_type="i9", document_number="123",
    )
    assert out.success
    assert out.status == "employment_authorised"
