package wfi.lcat

# LCAT (Labor Category) mapping for federal contract vehicles.
# Validates whether a candidate is qualified for a given LCAT on a given
# vehicle. The LCAT definitions live in data; this policy decides
# qualification given the data + the candidate's profile.

import rego.v1

# Built-in mini-catalogue. Production loads from `data.json` distributed
# alongside the policies (or from a sidecar API). Vehicles covered:
# OASIS, Alliant 2, CIO-SP4 — three LCATs each as a starter.
lcat_catalogue := {
    "OASIS": {
        "Subject Matter Expert III": {
            "min_years": 10,
            "education": "bachelors",
            "clearance_floor": "secret",
        },
        "Program Manager II": {
            "min_years": 8,
            "education": "bachelors",
            "clearance_floor": "public_trust",
        },
        "Engineer / Scientist III": {
            "min_years": 8,
            "education": "bachelors",
            "clearance_floor": "secret",
        },
    },
    "Alliant 2": {
        "Senior Cyber Engineer": {
            "min_years": 10,
            "education": "bachelors",
            "clearance_floor": "top_secret",
        },
        "Cloud Solution Architect": {
            "min_years": 8,
            "education": "bachelors",
            "clearance_floor": "secret",
        },
        "Data Scientist": {
            "min_years": 5,
            "education": "masters",
            "clearance_floor": "secret",
        },
    },
    "CIO-SP4": {
        "Health IT Architect": {
            "min_years": 10,
            "education": "masters",
            "clearance_floor": "public_trust",
        },
        "DevSecOps Engineer Senior": {
            "min_years": 6,
            "education": "bachelors",
            "clearance_floor": "secret",
        },
        "AI/ML Engineer": {
            "min_years": 5,
            "education": "masters",
            "clearance_floor": "public_trust",
        },
    },
}

clearance_rank := {
    "none": 0,
    "public_trust": 1,
    "secret": 2,
    "top_secret": 3,
    "ts_sci": 4,
}

education_rank := {
    "highschool": 0,
    "associates": 1,
    "bachelors": 2,
    "masters": 3,
    "doctorate": 4,
}

definition := lcat_catalogue[input.vehicle][input.lcat_code]

result := decision if {
    definition_present := definition
    candidate_clearance_ok := clearance_rank[input.candidate.clearance_type] >= clearance_rank[definition.clearance_floor]
    candidate_education_ok := education_rank[input.candidate.highest_education] >= education_rank[definition.education]
    candidate_years_ok := input.candidate.years_experience >= definition.min_years

    qualified := candidate_clearance_ok
    qualified2 := candidate_education_ok
    qualified3 := candidate_years_ok
    overall_qualified := qualified
    overall_qualified := false if not qualified
    overall_qualified := overall_qualified and qualified2 and qualified3

    verdict := "approved" if overall_qualified
    verdict := "rejected" if not overall_qualified

    decision := {
        "rule": "lcat_qualification",
        "verdict": verdict,
        "reasoning": sprintf(
            "vehicle=%v lcat=%v: clearance_ok=%v education_ok=%v years_ok=%v",
            [input.vehicle, input.lcat_code, candidate_clearance_ok, candidate_education_ok, candidate_years_ok],
        ),
        "details": {
            "lcat_definition": definition,
            "clearance_ok": candidate_clearance_ok,
            "education_ok": candidate_education_ok,
            "years_ok": candidate_years_ok,
        },
    }
}

# Fallback when the LCAT is not in the catalogue.
result := {
    "rule": "lcat_qualification",
    "verdict": "rejected",
    "reasoning": sprintf("LCAT %v not found in vehicle %v catalogue", [input.lcat_code, input.vehicle]),
    "details": {},
} if not definition
