"""CRUD + semantic search for candidates."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from pgvector.psycopg import register_vector_async

from candidates_svc.db import acquire
from wfi_schemas import Candidate, CandidateStatus

# Columns we read back into a Candidate. Keep the order tight so the
# RowMapper stays maintainable.
_SELECT_COLS = """
    id, created_at, updated_at, source, status,
    first_name, last_name, email, phone, linkedin_url,
    location_city, location_state, location_metro, willing_to_relocate, citizenship,
    career_history, career_arc_classification,
    compensation_history, comp_trajectory,
    primary_motion, secondary_motion,
    deal_cycle_min_days, deal_cycle_max_days, deal_cycle_avg_days,
    avg_acv, max_acv, methodology_experience,
    se_domains, se_vendor_specific, se_orientation, se_demo_skill_rating,
    clearance_type, polygraph, investigation_date, adjudication_date,
    clearance_status, read_on_history, facility_clearance_affiliations,
    itar_ear_eligible, sap_sar_access, deployability_score,
    last_contact_date, last_response_date, preferred_channel,
    response_rate_email, response_rate_linkedin, response_rate_phone,
    approachability_score, counteroffer_risk_score, availability_window,
    referral_connections,
    data_freshness_score, last_enrichment_date, profile_completeness_score, tags
"""


def _row_to_candidate(row: dict[str, Any]) -> Candidate:
    return Candidate(
        id=row["id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        source=row["source"],
        status=row["status"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        email=row["email"],
        phone=row["phone"],
        linkedin_url=row["linkedin_url"],
        location_city=row["location_city"],
        location_state=row["location_state"],
        location_metro=row["location_metro"],
        willing_to_relocate=row["willing_to_relocate"],
        citizenship=row["citizenship"],
        career_history=row["career_history"] or [],
        career_arc_classification=row["career_arc_classification"],
        compensation_history=row["compensation_history"] or [],
        comp_trajectory=row["comp_trajectory"],
        primary_motion=row["primary_motion"],
        secondary_motion=row["secondary_motion"],
        deal_cycle_min_days=row["deal_cycle_min_days"],
        deal_cycle_max_days=row["deal_cycle_max_days"],
        deal_cycle_avg_days=row["deal_cycle_avg_days"],
        avg_acv=float(row["avg_acv"]) if row["avg_acv"] is not None else None,
        max_acv=float(row["max_acv"]) if row["max_acv"] is not None else None,
        methodology_experience=row["methodology_experience"] or [],
        se_domains=row["se_domains"] or [],
        se_vendor_specific=row["se_vendor_specific"] or [],
        se_orientation=row["se_orientation"],
        se_demo_skill_rating=row["se_demo_skill_rating"],
        clearance_type=row["clearance_type"],
        polygraph=row["polygraph"],
        investigation_date=row["investigation_date"],
        adjudication_date=row["adjudication_date"],
        clearance_status=row["clearance_status"],
        read_on_history=row["read_on_history"] or [],
        facility_clearance_affiliations=row["facility_clearance_affiliations"] or [],
        itar_ear_eligible=row["itar_ear_eligible"],
        sap_sar_access=row["sap_sar_access"] or [],
        deployability_score=row["deployability_score"],
        engagement={
            "last_contact_date": row["last_contact_date"],
            "last_response_date": row["last_response_date"],
            "preferred_channel": row["preferred_channel"],
            "response_rate_email": row["response_rate_email"],
            "response_rate_linkedin": row["response_rate_linkedin"],
            "response_rate_phone": row["response_rate_phone"],
            "approachability_score": row["approachability_score"],
            "counteroffer_risk_score": row["counteroffer_risk_score"],
            "availability_window": row["availability_window"],
            "referral_connections": list(row["referral_connections"] or []),
        },
        data_freshness_score=row["data_freshness_score"],
        last_enrichment_date=row["last_enrichment_date"],
        profile_completeness_score=row["profile_completeness_score"],
        tags=list(row["tags"] or []),
    )


async def insert(candidate: Candidate, embedding: list[float] | None = None) -> UUID:
    """Insert a new candidate. Returns the assigned UUID."""
    async with acquire() as conn:
        await register_vector_async(conn)
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO candidates (
                    source, status, first_name, last_name, email, phone, linkedin_url,
                    location_city, location_state, location_metro, willing_to_relocate, citizenship,
                    career_history, career_arc_classification,
                    compensation_history, comp_trajectory,
                    primary_motion, secondary_motion,
                    deal_cycle_min_days, deal_cycle_max_days, deal_cycle_avg_days,
                    avg_acv, max_acv, methodology_experience,
                    se_domains, se_vendor_specific, se_orientation, se_demo_skill_rating,
                    clearance_type, polygraph, investigation_date, adjudication_date,
                    clearance_status, read_on_history, facility_clearance_affiliations,
                    itar_ear_eligible, sap_sar_access, deployability_score,
                    last_contact_date, last_response_date, preferred_channel,
                    response_rate_email, response_rate_linkedin, response_rate_phone,
                    approachability_score, counteroffer_risk_score, availability_window,
                    referral_connections,
                    profile_embedding, data_freshness_score, last_enrichment_date,
                    profile_completeness_score, tags
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s::jsonb, %s,
                    %s::jsonb, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s::jsonb, %s::jsonb,
                    %s, %s::jsonb, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s,
                    %s, %s, %s,
                    %s, %s
                )
                RETURNING id
                """,
                (
                    candidate.source, candidate.status,
                    candidate.first_name, candidate.last_name,
                    candidate.email, candidate.phone, candidate.linkedin_url,
                    candidate.location_city, candidate.location_state, candidate.location_metro,
                    candidate.willing_to_relocate, candidate.citizenship,
                    json.dumps([c.model_dump(mode="json") for c in candidate.career_history]),
                    candidate.career_arc_classification,
                    json.dumps([c.model_dump(mode="json") for c in candidate.compensation_history]),
                    candidate.comp_trajectory,
                    candidate.primary_motion, candidate.secondary_motion,
                    candidate.deal_cycle_min_days, candidate.deal_cycle_max_days,
                    candidate.deal_cycle_avg_days,
                    candidate.avg_acv, candidate.max_acv,
                    candidate.methodology_experience,
                    json.dumps(candidate.se_domains),
                    json.dumps(candidate.se_vendor_specific),
                    candidate.se_orientation, candidate.se_demo_skill_rating,
                    candidate.clearance_type, candidate.polygraph,
                    candidate.investigation_date, candidate.adjudication_date,
                    candidate.clearance_status,
                    json.dumps(candidate.read_on_history),
                    json.dumps(candidate.facility_clearance_affiliations),
                    candidate.itar_ear_eligible,
                    json.dumps(candidate.sap_sar_access),
                    candidate.deployability_score,
                    candidate.engagement.last_contact_date,
                    candidate.engagement.last_response_date,
                    candidate.engagement.preferred_channel,
                    candidate.engagement.response_rate_email,
                    candidate.engagement.response_rate_linkedin,
                    candidate.engagement.response_rate_phone,
                    candidate.engagement.approachability_score,
                    candidate.engagement.counteroffer_risk_score,
                    candidate.engagement.availability_window,
                    [str(x) for x in candidate.engagement.referral_connections],
                    embedding,
                    candidate.data_freshness_score,
                    candidate.last_enrichment_date,
                    candidate.profile_completeness_score,
                    candidate.tags,
                ),
            )
            row = await cur.fetchone()
            await conn.commit()
            return row[0]


async def get(candidate_id: UUID) -> Candidate | None:
    async with acquire() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"SELECT {_SELECT_COLS} FROM candidates WHERE id = %s", (candidate_id,)
            )
            row = await cur.fetchone()
            return _row_to_candidate(row) if row else None


async def update_status(candidate_id: UUID, status: CandidateStatus) -> None:
    async with acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE candidates SET status = %s WHERE id = %s",
                (status, candidate_id),
            )
            await conn.commit()


async def list_recent(limit: int = 50) -> list[Candidate]:
    async with acquire() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"SELECT {_SELECT_COLS} FROM candidates ORDER BY updated_at DESC LIMIT %s",
                (limit,),
            )
            rows = await cur.fetchall()
            return [_row_to_candidate(r) for r in rows]


# --- Semantic search --------------------------------------------------------

async def semantic_search(
    embedding: list[float],
    *,
    limit: int = 25,
    clearance_minimum: str | None = None,
    metro_area: str | None = None,
    motion: str | None = None,
) -> list[tuple[Candidate, float]]:
    """Return candidates ranked by cosine distance to ``embedding``.

    Optional structured filters are appended as WHERE clauses so we don't
    pay the recall cost of a pure vector search.
    """
    where: list[str] = []
    params: list[Any] = [embedding]
    if clearance_minimum:
        where.append("clearance_type >= %s::clearance_type")
        params.append(clearance_minimum)
    if metro_area:
        where.append("location_metro = %s")
        params.append(metro_area)
    if motion:
        where.append("primary_motion = %s::sales_motion")
        params.append(motion)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)

    sql = f"""
        SELECT {_SELECT_COLS},
               profile_embedding <=> %s::vector AS distance
        FROM candidates
        {where_sql}
        ORDER BY profile_embedding <=> %s::vector
        LIMIT %s
    """
    # The embedding parameter appears in SELECT, WHERE filters, ORDER BY.
    # Build the param list to match the placeholders.
    final_params: list[Any] = [embedding]
    if clearance_minimum:
        final_params.append(clearance_minimum)
    if metro_area:
        final_params.append(metro_area)
    if motion:
        final_params.append(motion)
    final_params.extend([embedding, limit])

    async with acquire() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, final_params)
            rows = await cur.fetchall()
            return [(_row_to_candidate(r), float(r["distance"])) for r in rows]
