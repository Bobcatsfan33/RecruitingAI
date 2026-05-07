package wfi.conversion_fee

# Temp-to-perm conversion fee economics.
#
# Inputs:
#   hours_worked:      number
#   bill_rate:         number  (per hour)
#   conversion_pct:    number  (e.g. 0.20 = 20% of first-year salary)
#   first_year_salary: number  (negotiated direct hire annual salary)
#   credit_per_hour:   number  (optional — default 0.0 means no hours-credit)
#   waiver_threshold_hours: number (optional — default 1000 hours worked)

import rego.v1

conversion_pct := input.conversion_pct if input.conversion_pct
conversion_pct := 0.20 if not input.conversion_pct

credit_per_hour := input.credit_per_hour if input.credit_per_hour
credit_per_hour := 0 if not input.credit_per_hour

waiver_threshold := input.waiver_threshold_hours if input.waiver_threshold_hours
waiver_threshold := 1000 if not input.waiver_threshold_hours

base_fee := input.first_year_salary * conversion_pct
credit := credit_per_hour * input.hours_worked
net_fee := max([base_fee - credit, 0])

waiver_eligible := input.hours_worked >= waiver_threshold

result := {
    "rule": "conversion_fee",
    "verdict": "approved",
    "details": {
        "base_fee": base_fee,
        "credit_applied": credit,
        "net_fee": net_fee,
        "waiver_eligible": waiver_eligible,
    },
    "reasoning": sprintf(
        "fee=%.2f, credit=%.2f, net=%.2f, hours=%v, waiver_at=%v",
        [base_fee, credit, net_fee, input.hours_worked, waiver_threshold],
    ),
}
