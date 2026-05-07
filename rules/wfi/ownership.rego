package wfi.ownership

# Ownership rules: submission exclusivity, RTR, DNC.
#
# Caller passes the precomputed ownership_status bundle from
# services/candidates/ownership_repo.ownership_status (one DB roundtrip,
# four booleans).

import rego.v1

# --- Submission exclusivity --------------------------------------------------

submission_exclusivity := {
    "rule": "submission_exclusivity",
    "verdict": verdict,
    "reasoning": reason,
    "details": {"has_exclusivity": input.has_exclusivity},
} if {
    verdict := "blocked" if input.has_exclusivity
    not_blocked := not input.has_exclusivity
    verdict := "allowed" if not_blocked
    reason := "candidate under exclusivity with this client" if input.has_exclusivity
    reason := "no exclusivity in effect" if not input.has_exclusivity
}

# --- Right to represent ------------------------------------------------------

right_to_represent := {
    "rule": "right_to_represent",
    "verdict": verdict,
    "reasoning": reason,
} if {
    verdict := "valid" if input.has_rtr
    verdict := "required" if not input.has_rtr
    reason := "RTR on file and current" if input.has_rtr
    reason := "obtain RTR before submission" if not input.has_rtr
}

# --- Do not contact ----------------------------------------------------------

do_not_contact := {
    "rule": "do_not_contact",
    "verdict": verdict,
    "reasoning": reason,
} if {
    verdict := "blocked" if input.is_dnc
    verdict := "allowed" if not input.is_dnc
    reason := "candidate is on DNC list" if input.is_dnc
    reason := "no DNC entries" if not input.is_dnc
}

# --- Bundled decision -------------------------------------------------------

result := {
    "rule": "ownership_bundle",
    "verdict": overall,
    "reasoning": message,
    "details": {
        "submission_exclusivity": submission_exclusivity,
        "right_to_represent": right_to_represent,
        "do_not_contact": do_not_contact,
    },
} if {
    blocked := input.has_exclusivity == true
    blocked2 := input.is_dnc == true
    requires_rtr := input.has_rtr == false
    overall := "blocked" if (blocked or blocked2)
    overall := "required" if (not blocked and not blocked2 and requires_rtr)
    overall := "allowed" if (not blocked and not blocked2 and not requires_rtr)
    message := "ownership check failed: see details" if overall == "blocked"
    message := "RTR required before submission" if overall == "required"
    message := "ownership clear; safe to submit" if overall == "allowed"
}
