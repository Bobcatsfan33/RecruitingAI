package wfi.comp

# Comp / market alignment rule.
#
# Inputs:
#   role_type:        string
#   seniority:        string
#   location:         string  (metro)
#   clearance_level:  string  (none|public_trust|secret|top_secret|ts_sci)
#   client_budget:    number  (annual OTE for salary; bill rate * 2080 for contract)
#   market_rate:      number  (caller supplies from comp benchmarks; if missing
#                              we fall back to a small built-in lookup table)

import rego.v1

default verdict := "feasible"
default reasoning := "client_budget within market alignment"

market_rate := input.market_rate if input.market_rate

market_rate := bench if not input.market_rate
bench := lookup if {
    lookup := market_lookup[input.role_type][input.seniority][input.location][input.clearance_level]
}

# Tiny built-in benchmark — sufficient for OPA-only sanity tests. Production
# wires `market_rate` from the comp benchmark service (Sprint 11).
market_lookup := {
    "ae": {
        "senior": {
            "DC Metro": {"ts_sci": 380000, "top_secret": 320000, "secret": 280000, "none": 240000},
            "SF Bay Area": {"none": 320000},
            "NYC Metro": {"none": 300000},
        }
    },
    "se": {
        "senior": {
            "DC Metro": {"ts_sci": 360000, "top_secret": 300000, "secret": 260000, "none": 220000},
            "SF Bay Area": {"none": 300000},
        }
    },
}

verdict := "infeasible" if {
    input.client_budget < market_rate * 0.85
}

verdict := "warning" if {
    input.client_budget >= market_rate * 0.85
    input.client_budget < market_rate * 0.95
}

reasoning := sprintf(
    "client_budget=%v, market=%v, gap=%.1f%%",
    [input.client_budget, market_rate, 100 * (input.client_budget - market_rate) / market_rate],
)

result := {
    "rule": "comp_market_alignment",
    "verdict": verdict,
    "reasoning": reasoning,
    "details": {
        "client_budget": input.client_budget,
        "market_rate": market_rate,
        "gap_pct": (input.client_budget - market_rate) / market_rate,
    },
    "suggestions": suggestions,
}

suggestions := ["increase budget toward market", "relax clearance one tier", "expand geography"] if verdict == "infeasible"
suggestions := ["share market data with client", "negotiate variable component"] if verdict == "warning"
suggestions := [] if verdict == "feasible"
