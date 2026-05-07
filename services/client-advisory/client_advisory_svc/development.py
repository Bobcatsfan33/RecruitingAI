"""Client Development agent — proactive triggers.

Watches public signals on tracked client companies + their competitors:
- Their `/careers` RSS or jobs page (if it exposes a feed).
- Their LinkedIn `/jobs` page (mock-only — restricted API).
- Press releases / earnings mentions (RSS feeds).
- Federal recompete timelines (no free GovWin API; mock).

Emits a list of `OutreachTrigger`s the AE team can act on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
import structlog

log = structlog.get_logger("client_advisory.development")


@dataclass
class OutreachTrigger:
    client_id: str | None
    client_name: str
    trigger_type: str   # job_posting | departure | earnings_growth | recompete
    title: str
    detail: str
    detected_at: datetime
    confidence: float = 0.7
    source_url: str | None = None


async def scan_careers_feed(
    *, client_id: str | None, client_name: str, feed_url: str,
    http: httpx.AsyncClient | None = None,
) -> list[OutreachTrigger]:
    """Pull a careers RSS feed; return a trigger per posting."""
    own = http is None
    client = http or httpx.AsyncClient(timeout=15.0)
    triggers: list[OutreachTrigger] = []
    try:
        try:
            response = await client.get(feed_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            log.warning("careers_feed_fetch_failed", url=feed_url, error=str(exc))
            return triggers
        feed = feedparser.parse(response.text)
        for entry in feed.entries[:50]:
            triggers.append(
                OutreachTrigger(
                    client_id=client_id,
                    client_name=client_name,
                    trigger_type="job_posting",
                    title=getattr(entry, "title", "(untitled)"),
                    detail=getattr(entry, "summary", "") or getattr(entry, "description", ""),
                    detected_at=datetime.now(timezone.utc),
                    source_url=getattr(entry, "link", None),
                )
            )
    finally:
        if own:
            await client.aclose()
    return triggers


def synthesize_recompete_trigger(
    *, client_id: str | None, client_name: str, contract_name: str,
    period_end: datetime,
) -> OutreachTrigger:
    days_to_end = (period_end - datetime.now(timezone.utc)).days
    return OutreachTrigger(
        client_id=client_id,
        client_name=client_name,
        trigger_type="recompete",
        title=f"{contract_name} recompete approaching",
        detail=f"Contract ends in {days_to_end} days.",
        detected_at=datetime.now(timezone.utc),
        confidence=0.95 if days_to_end < 180 else 0.7,
    )


@dataclass
class DevelopmentReport:
    client_id: str | None
    client_name: str
    triggers: list[OutreachTrigger] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "summary": self.summary,
            "triggers": [t.__dict__ for t in self.triggers],
        }
