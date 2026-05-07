"""Ownership queries: submissions, RTR, DNC, non-compete, non-solicit."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row

from candidates_svc.db import acquire


async def has_active_exclusivity(candidate_id: UUID, client_id: UUID) -> bool:
    """True if any submission for this candidate is still inside the
    exclusivity window with the given client."""
    async with acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1
                FROM submissions
                WHERE candidate_id = %s
                  AND client_id = %s
                  AND exclusivity_expires_at IS NOT NULL
                  AND exclusivity_expires_at > NOW()
                LIMIT 1
                """,
                (candidate_id, client_id),
            )
            return await cur.fetchone() is not None


async def has_valid_rtr(candidate_id: UUID, client_id: UUID) -> bool:
    async with acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT 1 FROM rights_to_represent
                WHERE candidate_id = %s
                  AND client_id = %s
                  AND revoked_at IS NULL
                  AND expires_at > NOW()
                LIMIT 1
                """,
                (candidate_id, client_id),
            )
            return await cur.fetchone() is not None


async def is_dnc(candidate_id: UUID, client_id: UUID | None = None) -> bool:
    """True for global or per-client DNC."""
    async with acquire() as conn:
        async with conn.cursor() as cur:
            if client_id is None:
                await cur.execute(
                    """
                    SELECT 1 FROM do_not_contact
                    WHERE candidate_id = %s AND client_id IS NULL
                    LIMIT 1
                    """,
                    (candidate_id,),
                )
            else:
                await cur.execute(
                    """
                    SELECT 1 FROM do_not_contact
                    WHERE candidate_id = %s
                      AND (client_id = %s OR client_id IS NULL)
                    LIMIT 1
                    """,
                    (candidate_id, client_id),
                )
            return await cur.fetchone() is not None


async def ownership_status(candidate_id: UUID, client_id: UUID) -> dict[str, Any]:
    """Bundle every ownership check for the rules engine in one query."""
    async with acquire() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT
                  EXISTS(SELECT 1 FROM submissions s
                         WHERE s.candidate_id = %(cid)s
                           AND s.client_id = %(clid)s
                           AND s.exclusivity_expires_at > NOW()) AS has_exclusivity,
                  EXISTS(SELECT 1 FROM rights_to_represent r
                         WHERE r.candidate_id = %(cid)s
                           AND r.client_id = %(clid)s
                           AND r.revoked_at IS NULL
                           AND r.expires_at > NOW()) AS has_rtr,
                  EXISTS(SELECT 1 FROM do_not_contact d
                         WHERE d.candidate_id = %(cid)s
                           AND (d.client_id = %(clid)s OR d.client_id IS NULL)) AS is_dnc,
                  EXISTS(SELECT 1 FROM non_competes n
                         WHERE n.candidate_id = %(cid)s
                           AND (n.expires_at IS NULL OR n.expires_at > NOW())) AS has_non_compete
                """,
                {"cid": candidate_id, "clid": client_id},
            )
            row = await cur.fetchone()
            return dict(row) if row else {
                "has_exclusivity": False,
                "has_rtr": False,
                "is_dnc": False,
                "has_non_compete": False,
            }


async def record_submission(
    candidate_id: UUID,
    requisition_id: UUID,
    client_id: UUID,
    *,
    exclusivity_days: int = 30,
) -> UUID:
    expires = datetime.now(timezone.utc).replace(microsecond=0)
    async with acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO submissions (
                    candidate_id, requisition_id, client_id, status,
                    submitted_at, exclusivity_expires_at
                )
                VALUES (%s, %s, %s, 'submitted', NOW(),
                        NOW() + (%s || ' days')::interval)
                ON CONFLICT (candidate_id, client_id, requisition_id)
                DO UPDATE SET
                    status = 'submitted',
                    submitted_at = NOW(),
                    exclusivity_expires_at = NOW() + EXCLUDED.exclusivity_expires_at - NOW()
                RETURNING id
                """,
                (candidate_id, requisition_id, client_id, exclusivity_days),
            )
            row = await cur.fetchone()
            await conn.commit()
            return row[0]
