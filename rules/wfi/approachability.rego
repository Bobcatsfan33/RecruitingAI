package wfi.approachability

# Approachability scoring (0-100): how likely is this candidate to engage
# with outreach right now? Higher = better.
#
# Inputs:
#   tenure_months_current_role:       number
#   months_since_last_promotion:      number  (null/-1 if unknown)
#   linkedin_recent_activity_score:   number 0..100
#   layoff_signal:                    bool   (employer in layoff cycle)
#   company_acquisition_signal:       bool
#   recent_job_change:                bool   (last job started < 6 months ago)
#   open_to_work_flag:                bool
#   prior_response_rate:              number 0..1 (null = unknown)

import rego.v1

base := 50

# Long tenure with no promotion is approachable (frustrated).
tenure_bump := 0
tenure_bump := 15 if input.tenure_months_current_role >= 36
tenure_bump := 10 if {
    input.tenure_months_current_role >= 24
    input.tenure_months_current_role < 36
}

promotion_bump := 0
promotion_bump := 10 if {
    input.months_since_last_promotion > 24
    input.months_since_last_promotion >= 0
}

# Negative signals.
recent_change_penalty := 0
recent_change_penalty := -25 if input.recent_job_change

# Strong positive signals.
open_to_work_bump := 0
open_to_work_bump := 25 if input.open_to_work_flag

layoff_bump := 0
layoff_bump := 15 if input.layoff_signal

acquisition_bump := 0
acquisition_bump := 8 if input.company_acquisition_signal

li_bump := 0
li_bump := 5 if input.linkedin_recent_activity_score >= 70

# Past responsiveness anchors.
response_bump := 0
response_bump := 10 if input.prior_response_rate >= 0.4

raw := base + tenure_bump + promotion_bump + open_to_work_bump + layoff_bump + acquisition_bump + li_bump + response_bump + recent_change_penalty
score := min([100, max([0, raw])])

result := {
    "rule": "approachability_score",
    "verdict": "approved",
    "reasoning": sprintf(
        "score=%v base=%v tenure=%v promo=%v change=%v open=%v layoff=%v acq=%v li=%v resp=%v",
        [score, base, tenure_bump, promotion_bump, recent_change_penalty,
         open_to_work_bump, layoff_bump, acquisition_bump, li_bump, response_bump],
    ),
    "details": {"score": score},
}
