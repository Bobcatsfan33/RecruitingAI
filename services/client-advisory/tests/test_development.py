"""Client Development trigger tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from client_advisory_svc.development import scan_careers_feed, synthesize_recompete_trigger

SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Acme Careers</title>
    <item>
      <title>Senior Cleared Sales Engineer</title>
      <description>TS/SCI required, NCR location.</description>
      <link>https://acme.com/jobs/1</link>
    </item>
    <item>
      <title>Federal Account Executive</title>
      <description>Hunter role, federal civilian agencies.</description>
      <link>https://acme.com/jobs/2</link>
    </item>
  </channel>
</rss>
"""


@pytest.mark.asyncio
async def test_scan_careers_feed_extracts_postings():
    async with respx.mock(assert_all_called=False) as router:
        router.get("https://acme.com/careers.rss").mock(
            return_value=httpx.Response(200, text=SAMPLE_FEED),
        )
        async with httpx.AsyncClient() as client:
            triggers = await scan_careers_feed(
                client_id="c1",
                client_name="Acme",
                feed_url="https://acme.com/careers.rss",
                http=client,
            )
    assert len(triggers) == 2
    assert all(t.trigger_type == "job_posting" for t in triggers)
    titles = {t.title for t in triggers}
    assert "Senior Cleared Sales Engineer" in titles


def test_recompete_trigger_high_confidence_when_close():
    out = synthesize_recompete_trigger(
        client_id="c1",
        client_name="Acme",
        contract_name="OASIS Pool 1",
        period_end=datetime.now(timezone.utc) + timedelta(days=60),
    )
    assert out.confidence > 0.9


def test_recompete_trigger_lower_confidence_when_far():
    out = synthesize_recompete_trigger(
        client_id=None,
        client_name="Acme",
        contract_name="OASIS Pool 1",
        period_end=datetime.now(timezone.utc) + timedelta(days=540),
    )
    assert out.confidence < 0.9
