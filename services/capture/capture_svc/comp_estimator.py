"""Compensation estimator per LCAT × location × clearance.

Returns a salary band + bill-rate band based on:
- A built-in baseline keyed by LCAT level (junior / mid / senior / SME)
- Location multiplier (NCR + SF Bay = 1.20, Tampa + Huntsville = 1.05, default 1.00)
- Clearance premium (TS = 1.15, TS/SCI = 1.30, +CI poly = 1.05, +full scope = 1.10, +lifestyle = 1.18)

These are starter ranges; production layers Sprint 11 verified-comp data
on top. The function returns a structured estimate the capture team can
defend to the proposal pricing lead.
"""

from __future__ import annotations

from dataclasses import dataclass


# Baseline annual salary bands by LCAT level (USD).
_BASELINE = {
    "junior":  (95_000, 130_000),
    "mid":     (130_000, 175_000),
    "senior":  (175_000, 235_000),
    "sme":     (220_000, 305_000),
}

_LOCATION_MULT = {
    "DC Metro":         1.20,
    "SF Bay Area":      1.20,
    "NYC Metro":        1.18,
    "Tampa Bay":        1.05,
    "Huntsville":       1.05,
    "San Antonio":      1.02,
    "Colorado Springs": 1.05,
}

_CLEARANCE_MULT = {
    "none":         1.00,
    "public_trust": 1.05,
    "secret":       1.10,
    "top_secret":   1.18,
    "ts_sci":       1.30,
}

_POLY_MULT = {
    "none":       1.00,
    "ci":         1.05,
    "full_scope": 1.10,
    "lifestyle":  1.18,
}


@dataclass
class CompEstimate:
    lcat_level: str
    location: str
    clearance: str
    polygraph: str
    salary_low: int
    salary_high: int
    bill_rate_low: float
    bill_rate_high: float
    multipliers: dict[str, float]


def estimate(
    *,
    lcat_level: str,
    location: str = "DC Metro",
    clearance: str = "secret",
    polygraph: str = "none",
    target_margin: float = 0.30,
) -> CompEstimate:
    base_low, base_high = _BASELINE.get(lcat_level, _BASELINE["senior"])
    loc_mult = _LOCATION_MULT.get(location, 1.00)
    clearance_mult = _CLEARANCE_MULT.get(clearance, 1.00)
    poly_mult = _POLY_MULT.get(polygraph, 1.00)
    total = loc_mult * clearance_mult * poly_mult
    salary_low = int(base_low * total)
    salary_high = int(base_high * total)
    # Bill rate ≈ pay-rate / (1 - margin); pay rate ≈ salary / 2080.
    bill_rate_low = round((salary_low / 2080) / (1 - target_margin), 2)
    bill_rate_high = round((salary_high / 2080) / (1 - target_margin), 2)
    return CompEstimate(
        lcat_level=lcat_level,
        location=location,
        clearance=clearance,
        polygraph=polygraph,
        salary_low=salary_low,
        salary_high=salary_high,
        bill_rate_low=bill_rate_low,
        bill_rate_high=bill_rate_high,
        multipliers={
            "location": loc_mult,
            "clearance": clearance_mult,
            "polygraph": poly_mult,
            "total": round(total, 4),
        },
    )
