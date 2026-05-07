package wfi.non_compete

# Non-compete enforceability lookup.
#
# Inputs:
#   has_non_compete:        bool
#   target_state:           string  (two-letter)
#   target_role:            string  (free text — for vertical/role overlap)
#   non_compete_industries: array of strings
#   non_compete_geography:  array of strings (states; empty = nationwide)
#   target_vertical:        string (e.g. "fintech", "healthcare")
#   target_company_state:   string

import rego.v1

# States that broadly ban or severely restrict non-competes.
banned_states := {"CA", "MN", "OK", "ND"}

# States with meaningful enforceability constraints.
restricted_states := {"WA", "CO", "IL", "MA", "OR", "VA", "MD", "RI", "NH", "DC", "NV", "ME"}

result := decision if {
    decision := {
        "rule": "non_compete_check",
        "verdict": verdict,
        "reasoning": reasoning,
        "details": {
            "target_state": target_state,
            "enforceability": enforceability,
        },
        "suggestions": suggestions,
    }
    target_state := input.target_state
    enforceability := "banned" if target_state in banned_states
    enforceability := "restricted" if target_state in restricted_states
    enforceability := "enforceable" if not (target_state in banned_states or target_state in restricted_states)

    no_nc := not input.has_non_compete
    verdict := "clear" if no_nc
    verdict := "clear" if (input.has_non_compete and enforceability == "banned")
    verdict := "risk" if (input.has_non_compete and enforceability == "enforceable" and _industry_overlap)
    verdict := "likely_clear" if (input.has_non_compete and enforceability == "restricted" and not _industry_overlap)
    verdict := "likely_clear" if (input.has_non_compete and enforceability == "enforceable" and not _industry_overlap)
    verdict := "risk" if (input.has_non_compete and enforceability == "restricted" and _industry_overlap)

    reasoning := "no active non-compete" if no_nc
    reasoning := sprintf("target state %v: %v; industry overlap=%v", [target_state, enforceability, _industry_overlap]) if input.has_non_compete

    suggestions := ["legal review of non-compete vs. target role", "delay start until expiry"] if verdict == "risk"
    suggestions := [] if verdict != "risk"
}

_industry_overlap if {
    some industry in input.non_compete_industries
    industry == input.target_vertical
}
