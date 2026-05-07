"""Market intelligence tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from market_svc.comp import CompPoint, benchmarks
from market_svc.competitive import CompetitiveSignals, evaluate
from market_svc.velocity import HiringSignal, report


def _comp(role="ae", seniority="senior", location="DC Metro", clearance="ts_sci",
          ote=300_000.0, w2=True) -> CompPoint:
    return CompPoint(
        role_type=role, seniority=seniority, location=location,
        clearance=clearance, ote=ote, w2_verified=w2,
    )


def test_comp_benchmarks_require_min_sample():
    points = [_comp(ote=300_000), _comp(ote=320_000)]
    assert benchmarks(points) == []


def test_comp_benchmarks_w2_only_filter():
    points = [
        _comp(ote=200_000, w2=True),
        _comp(ote=250_000, w2=True),
        _comp(ote=400_000, w2=False),
        _comp(ote=300_000, w2=True),
    ]
    out = benchmarks(points, w2_only=True)
    assert len(out) == 1
    assert out[0].sample_size == 3
    assert out[0].p50 == 250_000.0


def test_percentiles_increasing():
    points = [_comp(ote=v) for v in [200_000, 220_000, 250_000, 280_000, 320_000, 380_000, 420_000]]
    out = benchmarks(points)
    bench = out[0]
    assert bench.p25 < bench.p50 < bench.p75 < bench.p90


# --- velocity --------------------------------------------------------------

def test_velocity_30d_window():
    now = datetime.now(timezone.utc)
    signals = [
        HiringSignal(timestamp=now - timedelta(days=10), skill="snowflake"),
        HiringSignal(timestamp=now - timedelta(days=20), skill="snowflake"),
        HiringSignal(timestamp=now - timedelta(days=60), skill="snowflake"),
        HiringSignal(timestamp=now - timedelta(days=120), skill="snowflake"),
    ]
    rpt = report(signals, now=now)
    assert rpt.skill_demand_30d["snowflake"] == 2
    assert rpt.skill_demand_90d["snowflake"] == 3


def test_velocity_momentum_normalised_to_monthly():
    now = datetime.now(timezone.utc)
    signals = [HiringSignal(timestamp=now - timedelta(days=10), skill="x")] * 6
    rpt = report(signals, now=now)
    # 6 events in 30d / (6 events in 90d) * 3 = 3.0
    assert abs(rpt.momentum["x"] - 3.0) < 1e-6


# --- competitive ----------------------------------------------------------

def test_competitive_low_when_no_signals():
    out = evaluate(CompetitiveSignals(
        requisition_id="r-1", candidates_evaluated=10,
    ))
    assert out.band == "low"
    assert out.pressure_score < 35


def test_competitive_high_when_outreach_overlap_strong():
    out = evaluate(CompetitiveSignals(
        requisition_id="r-2",
        candidates_reporting_competing_outreach=8,
        candidates_evaluated=10,
        competing_agency_postings_count=6,
        candidates_with_competing_li_activity=4,
    ))
    assert out.band == "high"
    assert "compress timeline" in out.recommended_actions[0]


def test_competitive_components_breakdown():
    out = evaluate(CompetitiveSignals(
        requisition_id="r-3",
        candidates_reporting_competing_outreach=2,
        candidates_evaluated=4,
        competing_agency_postings_count=1,
    ))
    assert "competing_outreach_ratio" in out.components
    assert out.components["competing_outreach_ratio"] == 0.5
