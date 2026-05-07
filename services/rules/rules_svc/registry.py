"""Rule registry: maps short rule names to OPA policy paths.

Adding a new rule = adding a row here + a .rego file under /rules/wfi.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleSpec:
    name: str
    package: str       # e.g. "wfi.comp"
    rule: str = "result"  # the rule we extract from the package
    description: str = ""


REGISTRY: dict[str, RuleSpec] = {
    "comp_market_alignment": RuleSpec(
        name="comp_market_alignment",
        package="wfi.comp",
        description="Flag client budgets that fall below market rate.",
    ),
    "timeline_reasonableness": RuleSpec(
        name="timeline_reasonableness",
        package="wfi.timeline",
        description="Flag unrealistic fill timelines vs. clearance baseline.",
    ),
    "ownership_bundle": RuleSpec(
        name="ownership_bundle",
        package="wfi.ownership",
        description="Bundled exclusivity / RTR / DNC / non-compete check.",
    ),
    "submission_exclusivity": RuleSpec(
        name="submission_exclusivity",
        package="wfi.ownership",
        rule="submission_exclusivity",
    ),
    "right_to_represent": RuleSpec(
        name="right_to_represent",
        package="wfi.ownership",
        rule="right_to_represent",
    ),
    "do_not_contact": RuleSpec(
        name="do_not_contact",
        package="wfi.ownership",
        rule="do_not_contact",
    ),
    "margin_validation": RuleSpec(
        name="margin_validation",
        package="wfi.margin",
        description="Validate gross margin against floors.",
    ),
    "conversion_fee": RuleSpec(
        name="conversion_fee",
        package="wfi.conversion_fee",
        description="Compute net temp-to-perm conversion fee with hours-credit.",
    ),
    "co_employment_risk": RuleSpec(
        name="co_employment_risk",
        package="wfi.co_employment",
        description="Score co-employment exposure for ongoing contractor.",
    ),
    "non_compete_check": RuleSpec(
        name="non_compete_check",
        package="wfi.non_compete",
        description="Evaluate non-compete enforceability for the target role.",
    ),
    "req_mode_classification": RuleSpec(
        name="req_mode_classification",
        package="wfi.req_mode",
        description="Classify requisition as velocity / precision / balanced.",
    ),
    "lcat_qualification": RuleSpec(
        name="lcat_qualification",
        package="wfi.lcat",
        description="Validate candidate against contract-vehicle LCAT definition.",
    ),
    "approachability_score": RuleSpec(
        name="approachability_score",
        package="wfi.approachability",
        description="Score how reachable a candidate is right now.",
    ),
    "counteroffer_risk": RuleSpec(
        name="counteroffer_risk",
        package="wfi.counteroffer",
        description="Score how likely the candidate accepts a counteroffer.",
    ),
    "fiscal_year_urgency": RuleSpec(
        name="fiscal_year_urgency",
        package="wfi.fiscal_year",
        description="Adjust urgency for federal FY / CR cycles.",
    ),
}
