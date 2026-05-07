"""Silver-medalist buffer.

For every candidate at OFFER+, maintain `parallel_candidates_required`
warm backups at SUBMISSION. When a falloff event arrives, promote rank-1
silver and replace with rank-2; emit a routing decision for the
Pipeline Manager.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog

log = structlog.get_logger("pipeline.silver")


@dataclass
class SilverEntry:
    requisition_id: UUID
    candidate_id: UUID
    rank: int
    held_at: datetime
    promoted_at: datetime | None = None
    released_at: datetime | None = None


class SilverPool:
    """In-memory silver-medalist buffer.

    Production wires this against the `silver_medalists` table. The
    in-memory implementation here keeps the agent + tests pure.
    """

    def __init__(self) -> None:
        # Keyed by requisition_id; value is rank -> SilverEntry.
        self._by_req: dict[UUID, dict[int, SilverEntry]] = {}

    def hold(self, requisition_id: UUID, candidate_id: UUID, *, rank: int | None = None) -> SilverEntry:
        bucket = self._by_req.setdefault(requisition_id, {})
        next_rank = rank if rank is not None else (max(bucket, default=0) + 1)
        entry = SilverEntry(
            requisition_id=requisition_id,
            candidate_id=candidate_id,
            rank=next_rank,
            held_at=datetime.now(timezone.utc),
        )
        bucket[next_rank] = entry
        return entry

    def release(self, requisition_id: UUID, candidate_id: UUID) -> None:
        bucket = self._by_req.get(requisition_id, {})
        for rank, entry in list(bucket.items()):
            if entry.candidate_id == candidate_id:
                entry.released_at = datetime.now(timezone.utc)
                del bucket[rank]
                return

    def promote_next(self, requisition_id: UUID) -> SilverEntry | None:
        """Pop the rank-1 entry; subsequent entries renumber."""
        bucket = self._by_req.get(requisition_id, {})
        active = sorted(
            (e for e in bucket.values() if e.promoted_at is None and e.released_at is None),
            key=lambda e: e.rank,
        )
        if not active:
            return None
        promoted = active[0]
        promoted.promoted_at = datetime.now(timezone.utc)
        del bucket[promoted.rank]
        # Renumber survivors.
        survivors = sorted(bucket.values(), key=lambda e: e.rank)
        bucket.clear()
        for new_rank, entry in enumerate(survivors, start=1):
            entry.rank = new_rank
            bucket[new_rank] = entry
        log.info(
            "silver_medalist_promoted",
            req=str(requisition_id),
            candidate=str(promoted.candidate_id),
        )
        return promoted

    def health(self, requisition_id: UUID) -> dict[str, Any]:
        bucket = self._by_req.get(requisition_id, {})
        active = [e for e in bucket.values() if e.released_at is None and e.promoted_at is None]
        return {
            "requisition_id": str(requisition_id),
            "active_silver_count": len(active),
            "ranks": [e.rank for e in sorted(active, key=lambda e: e.rank)],
        }
