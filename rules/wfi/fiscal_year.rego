package wfi.fiscal_year

# Federal fiscal-year + Continuing-Resolution awareness.
# Adjusts urgency for federal hiring cycles.
#
# Inputs:
#   today:                ISO date string  (defaults to system time)
#   under_continuing_resolution: bool
#   pending_recompete_within_days: number  (-1 if none)

import rego.v1

# US fiscal year runs Oct 1 - Sep 30. Q4 (Jul-Sep) is the spend-down sprint.

today := input.today if input.today
month := time.parse_rfc3339_ns(time.add_date(today, 0, 0, 0)) if today

# Use a static computation for simplicity — caller passes the current month.
month_num := input.month_num if input.month_num

is_fy_q4 := false
is_fy_q4 := true if month_num == 7
is_fy_q4 := true if month_num == 8
is_fy_q4 := true if month_num == 9

is_fy_kickoff := false
is_fy_kickoff := true if month_num == 10
is_fy_kickoff := true if month_num == 11

urgency := "elevated" if is_fy_q4
urgency := "elevated" if input.pending_recompete_within_days >= 0
urgency := "elevated" if input.pending_recompete_within_days <= 90
urgency := "soft" if input.under_continuing_resolution
urgency := "normal" if not (is_fy_q4 or input.under_continuing_resolution)

reasoning := sprintf(
    "month=%v, FYQ4=%v, FY_kickoff=%v, CR=%v, recompete_within=%v",
    [month_num, is_fy_q4, is_fy_kickoff, input.under_continuing_resolution, input.pending_recompete_within_days],
)

result := {
    "rule": "fiscal_year_urgency",
    "verdict": urgency,
    "reasoning": reasoning,
    "details": {
        "fiscal_q4": is_fy_q4,
        "fiscal_kickoff": is_fy_kickoff,
        "continuing_resolution": input.under_continuing_resolution,
    },
}
