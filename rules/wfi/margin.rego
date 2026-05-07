package wfi.margin

# Margin management for contract staffing placements.
#
# Inputs:
#   bill_rate:    number (per hour)
#   pay_rate:     number (per hour)
#   benefits_cost: number (per hour, default $4.50)
#   burden_rate:  number (per hour, default $1.20 — payroll tax)

import rego.v1

benefits := input.benefits_cost if input.benefits_cost
benefits := 4.5 if not input.benefits_cost

burden := input.burden_rate if input.burden_rate
burden := 1.2 if not input.burden_rate

gross_margin := (input.bill_rate - input.pay_rate - benefits - burden) / input.bill_rate

default verdict := "approved"

verdict := "rejected" if gross_margin < 0.15
verdict := "warning" if {
    gross_margin >= 0.15
    gross_margin < 0.20
}
verdict := "warning" if gross_margin > 0.45

reasoning := sprintf(
    "gross_margin=%.1f%% (bill=%v, pay=%v, benefits=%v, burden=%v)",
    [gross_margin * 100, input.bill_rate, input.pay_rate, benefits, burden],
)

result := {
    "rule": "margin_validation",
    "verdict": verdict,
    "reasoning": reasoning,
    "details": {
        "bill_rate": input.bill_rate,
        "pay_rate": input.pay_rate,
        "benefits_cost": benefits,
        "burden_rate": burden,
        "gross_margin": gross_margin,
    },
    "suggestions": suggestions,
}

suggestions := ["raise bill rate", "lower pay rate", "decline at this margin"] if verdict == "rejected"
suggestions := ["escalate to management for thin-margin approval"] if verdict == "warning"
suggestions := [] if verdict == "approved"
