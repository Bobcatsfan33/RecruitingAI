"""Capture-service tests covering feasibility, heat maps, comp, LOIs."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from capture_svc.comp_estimator import estimate
from capture_svc.feasibility import LcatRequirement, analyze
from capture_svc.heatmap import CandidateFacet, build, summarise_by_clearance
from capture_svc.loi import LoiStatus, draft_loi, expired, package


# --- feasibility -----------------------------------------------------------

def test_feasibility_zero_supply_is_infeasible():
    reqs = [LcatRequirement(lcat_code="L1", headcount=5, clearance_required="ts_sci")]
    score = analyze(reqs)
    assert score.overall_status == "infeasible"
    assert score.estimates[0].available_now_pool == 0


def test_feasibility_with_ample_supply_is_feasible():
    def counter(lcat, clearance, poly, location, available_now):
        return 50 if available_now else 80
    reqs = [LcatRequirement(lcat_code="L1", headcount=5, clearance_required="ts_sci")]
    score = analyze(reqs, count_fn=counter)
    assert score.overall_status == "feasible"
    assert score.estimates[0].in_pipeline == 30


def test_feasibility_difficult_band():
    def counter(lcat, clearance, poly, location, available_now):
        return 3 if available_now else 6
    reqs = [LcatRequirement(lcat_code="L1", headcount=10, clearance_required="ts_sci")]
    score = analyze(reqs, count_fn=counter)
    assert score.overall_status in {"difficult", "infeasible"}


# --- heat map --------------------------------------------------------------

def test_heatmap_aggregates_by_facet_combo():
    facets = [
        CandidateFacet("ts_sci", "DC Metro", "Senior SE", True),
        CandidateFacet("ts_sci", "DC Metro", "Senior SE", False),
        CandidateFacet("ts_sci", "Tampa Bay", "Senior SE", True),
        CandidateFacet("secret", "DC Metro", "Senior SE", True),
    ]
    cells = build(facets)
    dc_ts = next(c for c in cells if c.metro == "DC Metro" and c.clearance == "ts_sci")
    assert dc_ts.count == 2
    assert dc_ts.available_now_count == 1


def test_heatmap_summary_by_clearance_metro():
    facets = [
        CandidateFacet("ts_sci", "DC Metro", "X", True),
        CandidateFacet("ts_sci", "DC Metro", "Y", False),
        CandidateFacet("secret", "Tampa Bay", "Z", True),
    ]
    summary = summarise_by_clearance(build(facets))
    assert summary["ts_sci"]["DC Metro"] == 2
    assert summary["secret"]["Tampa Bay"] == 1


# --- comp estimator -------------------------------------------------------

def test_comp_estimate_clearance_premium_increases_band():
    plain = estimate(lcat_level="senior", clearance="none", polygraph="none")
    cleared = estimate(lcat_level="senior", clearance="ts_sci", polygraph="lifestyle")
    assert cleared.salary_low > plain.salary_low
    assert cleared.salary_high > plain.salary_high


def test_comp_estimate_dc_metro_costs_more_than_tampa():
    dc = estimate(lcat_level="senior", location="DC Metro")
    tampa = estimate(lcat_level="senior", location="Tampa Bay")
    assert dc.salary_high > tampa.salary_high


def test_bill_rate_respects_target_margin():
    out = estimate(lcat_level="mid", target_margin=0.30)
    pay_rate = out.salary_low / 2080
    expected_bill = pay_rate / (1 - 0.30)
    assert abs(out.bill_rate_low - round(expected_bill, 2)) < 0.05


# --- LOI -----------------------------------------------------------------

def test_loi_draft_includes_summary():
    loi = draft_loi(
        candidate_id=uuid4(),
        opportunity_name="OASIS Cyber Pursuit",
        contract_vehicle="OASIS",
        lcat_code="Subject Matter Expert III",
        period_of_performance_start=date(2026, 7, 1),
        period_of_performance_end=date(2027, 6, 30),
        proposed_salary=240_000,
    )
    assert "OASIS" in loi.contingent_offer_summary
    assert "240,000" in loi.contingent_offer_summary


def test_loi_package_acceptance_rate():
    candidate = uuid4()
    lois = [
        draft_loi(
            candidate_id=candidate, opportunity_name="X", contract_vehicle="Y",
            lcat_code="L", period_of_performance_start=date.today(),
            period_of_performance_end=date.today(),
        )
        for _ in range(3)
    ]
    lois[0].status = LoiStatus.SIGNED
    pkg = package("X", "Y", lois)
    assert abs(pkg.acceptance_rate() - 1 / 3) < 1e-6


def test_loi_expiry_check():
    from datetime import datetime, timedelta, timezone
    loi = draft_loi(
        candidate_id=uuid4(),
        opportunity_name="X",
        contract_vehicle="Y",
        lcat_code="L",
        period_of_performance_start=date.today(),
        period_of_performance_end=date.today(),
    )
    assert not expired(loi)
    assert expired(loi, now=datetime.now(timezone.utc) + timedelta(days=400))
