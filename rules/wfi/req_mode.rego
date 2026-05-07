package wfi.req_mode

# Velocity vs. precision req classification.
#
# Inputs:
#   req_type:           "precision"|"velocity"|"pre_award"|"contingent"|"direct_hire"
#   urgency:            "critical_48h"|"standard_2wk"|"pipeline_30d"|"pre_award_speculative"
#   role_complexity:    number 1..10
#   client_preference:  "speed"|"quality"|"balanced"
#   fill_count:         number  (how many positions on this req)
#   comp_total:         number  (OTE for salary; bill * 2080 for contract)

import rego.v1

default verdict := "balanced"

verdict := "velocity" if input.urgency == "critical_48h"
verdict := "velocity" if {
    input.fill_count > 5
    input.role_complexity < 3
}
verdict := "velocity" if {
    input.req_type == "contingent"
    input.client_preference == "speed"
}
verdict := "precision" if input.role_complexity >= 7
verdict := "precision" if input.comp_total > 300000
verdict := "precision" if {
    input.req_type == "direct_hire"
    not input.urgency == "critical_48h"
}

reasoning := sprintf(
    "req_type=%v, urgency=%v, complexity=%v, fill_count=%v, comp=%v",
    [input.req_type, input.urgency, input.role_complexity, input.fill_count, input.comp_total],
)

result := {
    "rule": "req_mode_classification",
    "verdict": verdict,
    "reasoning": reasoning,
    "details": {"mode": verdict},
}
