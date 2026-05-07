"""Local helper for temp-to-perm conversion fee math.

Backed by the OPA `conversion_fee` rule when a service is reachable;
the local copy here is for fast dashboard rendering + tests.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConversionFeeBreakdown:
    base_fee: float
    credit: float
    net_fee: float
    waiver_eligible: bool


def compute(
    *,
    hours_worked: int,
    bill_rate: float,
    first_year_salary: int,
    conversion_pct: float = 0.20,
    credit_per_hour: float = 0.0,
    waiver_threshold_hours: int = 1000,
) -> ConversionFeeBreakdown:
    base = first_year_salary * conversion_pct
    credit = hours_worked * credit_per_hour
    net = max(base - credit, 0.0)
    return ConversionFeeBreakdown(
        base_fee=round(base, 2),
        credit=round(credit, 2),
        net_fee=round(net, 2),
        waiver_eligible=hours_worked >= waiver_threshold_hours,
    )


def utilisation_rate(
    *,
    bench_hours: int,
    billable_hours: int,
) -> float:
    total = bench_hours + billable_hours
    if total <= 0:
        return 0.0
    return round(billable_hours / total, 4)
