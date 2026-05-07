"""Mock enrichment adapter behaviour."""

from __future__ import annotations

import pytest

from wfi_data.enrichment import MockEnrichmentAdapter


@pytest.mark.asyncio
async def test_mock_enrich_by_email_synthesises_a_record():
    adapter = MockEnrichmentAdapter()
    result = await adapter.enrich_by_email("alice@example.com")
    assert result.found
    assert result.email == "alice@example.com"
    assert result.linkedin_url and "alice" in result.linkedin_url
    assert adapter.calls == [("email", {"email": "alice@example.com"})]


@pytest.mark.asyncio
async def test_mock_can_be_configured_to_miss():
    adapter = MockEnrichmentAdapter(default_found=False)
    result = await adapter.enrich_by_linkedin("https://linkedin.com/in/x")
    assert not result.found
    assert result.email is None


@pytest.mark.asyncio
async def test_mock_enrich_by_name_company_builds_email():
    adapter = MockEnrichmentAdapter()
    result = await adapter.enrich_by_name_company(name="Sam Lee", company="Acme Corp")
    assert result.found
    assert result.email and result.email.startswith("sam.lee@")
