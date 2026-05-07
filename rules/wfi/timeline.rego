package wfi.timeline

# Timeline reasonableness — flags requisitions whose fill window is below
# the operational baseline given clearance + role complexity.
#
# Inputs:
#   clearance_requirement:    string
#   new_investigation_required: bool
#   timeline_days:            number
#   role_complexity:          number 1..10  (10 = most complex)
#   location:                 string

import rego.v1

default verdict := "feasible"
default reasoning := ""

# Hard infeasibility for new TS/SCI investigations under a year.
verdict := "infeasible" if {
    input.clearance_requirement == "ts_sci"
    input.new_investigation_required
    input.timeline_days < 365
}

verdict := "infeasible" if {
    input.clearance_requirement == "top_secret"
    input.new_investigation_required
    input.timeline_days < 180
}

# Baseline fill times by clearance (calendar days) for active candidates.
baseline_days := {
    "none":        45,
    "public_trust": 60,
    "secret":      75,
    "top_secret":  120,
    "ts_sci":      150,
}

baseline := baseline_days[input.clearance_requirement] if input.clearance_requirement
complexity := input.role_complexity if input.role_complexity
complexity := 5 if not input.role_complexity

adjusted_baseline := baseline * (1 + (complexity - 5) * 0.1)

verdict := "warning" if {
    not _hard_infeasible
    input.timeline_days < adjusted_baseline * 0.5
}

_hard_infeasible if {
    input.clearance_requirement == "ts_sci"
    input.new_investigation_required
    input.timeline_days < 365
}

_hard_infeasible if {
    input.clearance_requirement == "top_secret"
    input.new_investigation_required
    input.timeline_days < 180
}

reasoning := sprintf(
    "timeline=%v days, baseline=%.0f, complexity=%v",
    [input.timeline_days, adjusted_baseline, complexity],
)

result := {
    "rule": "timeline_reasonableness",
    "verdict": verdict,
    "reasoning": reasoning,
    "details": {
        "timeline_days": input.timeline_days,
        "baseline_days": adjusted_baseline,
    },
    "suggestions": suggestions,
}

suggestions := ["surface candidates with active clearance only", "negotiate timeline"] if verdict == "warning"
suggestions := ["client must accept longer timeline or relax clearance"] if verdict == "infeasible"
suggestions := [] if verdict == "feasible"
