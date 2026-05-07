"""Intake feasibility tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from client_advisory_svc.intake import analyze
from wfi_rules_sdk import MockRulesClient
from wfi_rules_sdk.client import RuleEvaluation
from wfi_schemas import ClearanceType, CompType, Requisition, ReqType


def _req() -> Requisition:
    return Requisition(
        client_id=uuid4(),
        req_type=ReqType.PRECISION,
        title="Senior AE",
        comp_type=CompType.SALARY,
        budget_max=240_000,
        clearance_minimum=ClearanceType.TS_SCI,
        sla_days_to_fill=60,
        location_requirements={"metro": "DC Metro"},
    )


@pytest.mark.asyncio
async def test_feasible_when_rules_say_so():
    rules = MockRulesClient()
    rules.register("comp_market_alignment", lambda _: RuleEvaluation(
        rule="comp_market_alignment", verdict="feasible", reasoning="ok",
    ))
    rules.register("timeline_reasonableness", lambda _: RuleEvaluation(
        rule="timeline_reasonableness", verdict="feasible", reasoning="ok",
    ))
    report = await analyze(_req(), rules=rules)
    assert report.overall_verdict == "feasible"


@pytest.mark.asyncio
async def test_infeasible_short_circuits():
    rules = MockRulesClient()
    rules.register("comp_market_alignment", lambda _: RuleEvaluation(
        rule="comp_market_alignment", verdict="infeasible", reasoning="comp too low",
    ))
    rules.register("timeline_reasonableness", lambda _: RuleEvaluation(
        rule="timeline_reasonableness", verdict="warning", reasoning="aggressive",
    ))
    report = await analyze(_req(), rules=rules)
    assert report.overall_verdict == "infeasible"
    # Should produce relaxation options.
    assert any(o["lever"] == "comp" for o in report.relaxation_options)
    assert any(o["lever"] == "clearance" for o in report.relaxation_options)


@pytest.mark.asyncio
async def test_warning_rolls_up_to_difficult():
    rules = MockRulesClient()
    rules.register("comp_market_alignment", lambda _: RuleEvaluation(
        rule="comp_market_alignment", verdict="warning", reasoning="thin",
    ))
    rules.register("timeline_reasonableness", lambda _: RuleEvaluation(
        rule="timeline_reasonableness", verdict="feasible", reasoning="ok",
    ))
    report = await analyze(_req(), rules=rules)
    assert report.overall_verdict == "difficult"
