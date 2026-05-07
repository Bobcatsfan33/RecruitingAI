package wfi.co_employment

# Co-employment risk scoring for contractors.
#
# Inputs:
#   tenure_months:         number
#   hours_per_week:        number
#   supervision_model:     "direct_client_management" | "vendor_managed" | "self_directed"

import rego.v1

risk_score := score if {
    base := 0
    a := base + 30 if input.tenure_months > 18 else base
    b := a + 20 if input.tenure_months > 24 else a
    c := b + 15 if input.hours_per_week >= 30 else b
    d := c + 10 if input.hours_per_week >= 40 else c
    e := d + 25 if input.supervision_model == "direct_client_management" else d
    score := e
}

default verdict := "low_risk"
verdict := "medium_risk" if {
    risk_score >= 30
    risk_score < 50
}
verdict := "high_risk" if risk_score >= 50

reasoning := sprintf(
    "risk_score=%v, tenure_months=%v, hours_per_week=%v, supervision=%v",
    [risk_score, input.tenure_months, input.hours_per_week, input.supervision_model],
)

result := {
    "rule": "co_employment_risk",
    "verdict": verdict,
    "reasoning": reasoning,
    "details": {
        "risk_score": risk_score,
    },
    "suggestions": suggestions,
}

suggestions := ["restructure engagement", "convert to direct hire", "reduce hours below 30"] if verdict == "high_risk"
suggestions := ["monitor at next checkpoint", "review supervision model"] if verdict == "medium_risk"
suggestions := [] if verdict == "low_risk"
