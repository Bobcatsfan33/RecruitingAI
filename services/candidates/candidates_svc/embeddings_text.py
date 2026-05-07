"""Build the canonical text used for candidate + requisition embeddings.

Same function applied on both sides keeps cosine similarity meaningful.
"""

from __future__ import annotations

from wfi_schemas import Candidate, Requisition


def candidate_embedding_text(c: Candidate) -> str:
    parts: list[str] = []
    parts.append(f"{c.first_name} {c.last_name}")
    if c.location_metro:
        parts.append(f"Located in {c.location_metro}, {c.location_state}")
    if c.clearance_type and c.clearance_type != "none":
        clearance = c.clearance_type.upper().replace("_", " ")
        poly = (c.polygraph or "none").upper().replace("_", " ")
        parts.append(f"Clearance: {clearance}, polygraph: {poly}")
    if c.primary_motion:
        parts.append(f"Primary sales motion: {c.primary_motion}")
    if c.methodology_experience:
        parts.append("Methodologies: " + ", ".join(c.methodology_experience))
    for entry in c.career_history[:6]:
        parts.append(
            f"- {entry.title} at {entry.company} "
            f"({entry.start_date or '?'} – {entry.end_date or 'present'})"
        )
    if c.tags:
        parts.append("Tags: " + ", ".join(c.tags))
    return "\n".join(parts)


def requisition_embedding_text(r: Requisition) -> str:
    parts: list[str] = []
    parts.append(f"{r.title} ({r.req_type})")
    if r.location_requirements:
        parts.append(f"Location requirements: {r.location_requirements}")
    if r.clearance_minimum and r.clearance_minimum != "none":
        clearance = r.clearance_minimum.upper().replace("_", " ")
        poly = (r.polygraph_required or "none").upper().replace("_", " ")
        parts.append(f"Clearance required: {clearance}, polygraph: {poly}")
    if r.motion_type_required:
        parts.append(f"Sales motion required: {r.motion_type_required}")
    if r.must_have_skills:
        parts.append("Must-have skills: " + ", ".join(r.must_have_skills))
    if r.nice_to_have_skills:
        parts.append("Nice-to-have skills: " + ", ".join(r.nice_to_have_skills))
    if r.years_experience_min is not None:
        parts.append(f"Experience min: {r.years_experience_min} years")
    if r.lcat_code:
        parts.append(f"LCAT: {r.lcat_code} on {r.contract_vehicle}")
    return "\n".join(parts)
