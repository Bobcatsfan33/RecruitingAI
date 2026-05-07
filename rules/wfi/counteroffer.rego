package wfi.counteroffer

# Counteroffer risk scoring (0-100). Higher = more likely the candidate
# will accept a counteroffer from their current employer mid-pipeline.
#
# Inputs:
#   tenure_months_current_role:   number
#   high_performer_signals:       bool
#   recent_promotion:             bool   (last 12 months)
#   compensation_gap_pct:         number  (new offer vs. current — positive = better)
#   current_employer_tier:        "platform"|"established"|"growth"|"early"
#   sole_income_household:        bool
#   has_unvested_equity:          bool
#   stated_motivation_score:      number 0..100  (from screen interview; 100 = strongly motivated to leave)

import rego.v1

base := 30

# Long tenure increases attachment.
tenure_bump := 15 if input.tenure_months_current_role >= 60
tenure_bump := 10 if {
    input.tenure_months_current_role >= 36
    input.tenure_months_current_role < 60
}
tenure_bump := 0 if input.tenure_months_current_role < 36

high_performer_bump := 15 if input.high_performer_signals
high_performer_bump := 0 if not input.high_performer_signals

promotion_bump := 12 if input.recent_promotion
promotion_bump := 0 if not input.recent_promotion

# Larger gap reduces counteroffer risk (employer has to match a bigger jump).
gap_bump := -20 if input.compensation_gap_pct >= 0.30
gap_bump := -10 if {
    input.compensation_gap_pct >= 0.15
    input.compensation_gap_pct < 0.30
}
gap_bump := 0 if input.compensation_gap_pct < 0.15

employer_bump := 10 if input.current_employer_tier == "platform"
employer_bump := 5 if input.current_employer_tier == "established"
employer_bump := 0 if not (input.current_employer_tier == "platform" or input.current_employer_tier == "established")

equity_bump := 12 if input.has_unvested_equity
equity_bump := 0 if not input.has_unvested_equity

household_bump := 8 if input.sole_income_household
household_bump := 0 if not input.sole_income_household

motivation_penalty := -25 if input.stated_motivation_score >= 80
motivation_penalty := -10 if {
    input.stated_motivation_score >= 60
    input.stated_motivation_score < 80
}
motivation_penalty := 0 if input.stated_motivation_score < 60

raw := base + tenure_bump + high_performer_bump + promotion_bump + gap_bump + employer_bump + equity_bump + household_bump + motivation_penalty
score := min([100, max([0, raw])])

verdict := "high_risk" if score >= 65
verdict := "medium_risk" if {
    score >= 35
    score < 65
}
verdict := "low_risk" if score < 35

result := {
    "rule": "counteroffer_risk",
    "verdict": verdict,
    "reasoning": sprintf("counteroffer_risk_score=%v", [score]),
    "details": {"score": score},
    "suggestions": suggestions,
}

suggestions := ["embed counteroffer inoculation in outreach", "accelerate timeline", "stretch the offer beyond current band"] if verdict == "high_risk"
suggestions := ["monitor sentiment during close protection"] if verdict == "medium_risk"
suggestions := [] if verdict == "low_risk"
