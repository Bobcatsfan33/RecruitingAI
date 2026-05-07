"""Enrichment adapters.

Apollo + ZoomInfo are the canonical providers for US contact enrichment;
both are paid and have no free public API tier. We ship:

- ``EnrichmentAdapter`` Protocol — every implementation matches this surface.
- ``ApolloEnrichmentAdapter`` — real Apollo client. No-ops to mock if no key.
- ``MockEnrichmentAdapter`` — deterministic synthetic enrichment for tests.

The candidate service (Sprint 1) calls the configured adapter from a
Temporal activity so retries + DLQ behaviour are uniform.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
import structlog

log = structlog.get_logger("wfi.data.enrichment")


@dataclass
class EnrichmentResult:
    found: bool
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    location_city: str | None = None
    location_state: str | None = None
    employer: str | None = None
    title: str | None = None
    seniority: str | None = None
    departments: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    provider: str = ""


class EnrichmentAdapter(Protocol):
    name: str

    async def enrich_by_email(self, email: str) -> EnrichmentResult: ...
    async def enrich_by_linkedin(self, linkedin_url: str) -> EnrichmentResult: ...
    async def enrich_by_name_company(self, *, name: str, company: str) -> EnrichmentResult: ...


class MockEnrichmentAdapter:
    name = "mock"

    def __init__(self, *, default_found: bool = True) -> None:
        self._default_found = default_found
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def enrich_by_email(self, email: str) -> EnrichmentResult:
        self.calls.append(("email", {"email": email}))
        if not self._default_found:
            return EnrichmentResult(found=False, provider=self.name)
        local, _, _domain = email.partition("@")
        return EnrichmentResult(
            found=True,
            email=email,
            phone="+15555550100",
            linkedin_url=f"https://www.linkedin.com/in/{local}-mock",
            location_city="Reston",
            location_state="VA",
            employer="Mock Corp",
            title="Senior Account Executive",
            seniority="senior",
            departments=["sales"],
            provider=self.name,
            raw={"mock": True},
        )

    async def enrich_by_linkedin(self, linkedin_url: str) -> EnrichmentResult:
        self.calls.append(("linkedin", {"linkedin_url": linkedin_url}))
        return EnrichmentResult(
            found=self._default_found,
            linkedin_url=linkedin_url,
            email="enriched@mock.local" if self._default_found else None,
            employer="Mock Corp" if self._default_found else None,
            provider=self.name,
        )

    async def enrich_by_name_company(self, *, name: str, company: str) -> EnrichmentResult:
        self.calls.append(("name_company", {"name": name, "company": company}))
        slug = name.lower().replace(" ", ".")
        return EnrichmentResult(
            found=self._default_found,
            email=f"{slug}@{company.lower().replace(' ', '')}.com" if self._default_found else None,
            employer=company,
            provider=self.name,
        )


class ApolloEnrichmentAdapter:
    """Real Apollo.io People Match v1 adapter.

    Apollo expects an `api_key` parameter (not a header). Endpoint shape is
    POST https://api.apollo.io/v1/people/match with one of email | linkedin_url
    | name+organization_name. Returns a `person` object with phone+org info.
    Free trial credits exist but no perpetual free tier — leave the env var
    empty to fall back to mock mode.
    """

    name = "apollo"

    def __init__(self, *, api_key: str | None = None) -> None:
        key = api_key or os.environ.get("APOLLO_API_KEY")
        if not key:
            raise RuntimeError("APOLLO_API_KEY not set; use MockEnrichmentAdapter")
        self._key = key
        self._client = httpx.AsyncClient(
            base_url="https://api.apollo.io/v1",
            headers={"content-type": "application/json"},
            timeout=15.0,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def enrich_by_email(self, email: str) -> EnrichmentResult:
        return await self._call({"api_key": self._key, "email": email})

    async def enrich_by_linkedin(self, linkedin_url: str) -> EnrichmentResult:
        return await self._call({"api_key": self._key, "linkedin_url": linkedin_url})

    async def enrich_by_name_company(self, *, name: str, company: str) -> EnrichmentResult:
        return await self._call(
            {"api_key": self._key, "name": name, "organization_name": company}
        )

    async def _call(self, payload: dict[str, Any]) -> EnrichmentResult:
        try:
            response = await self._client.post("/people/match", json=payload)
        except httpx.HTTPError as exc:
            log.warning("apollo_request_failed", error=str(exc))
            return EnrichmentResult(found=False, provider=self.name)
        if response.status_code == 404:
            return EnrichmentResult(found=False, provider=self.name)
        if response.status_code >= 400:
            log.warning("apollo_error", status=response.status_code, body=response.text[:200])
            return EnrichmentResult(found=False, provider=self.name)
        body = response.json()
        person = body.get("person") or {}
        if not person:
            return EnrichmentResult(found=False, provider=self.name, raw=body)
        org = person.get("organization") or {}
        return EnrichmentResult(
            found=True,
            email=person.get("email"),
            phone=person.get("sanitized_phone") or person.get("phone_number"),
            linkedin_url=person.get("linkedin_url"),
            location_city=person.get("city"),
            location_state=person.get("state"),
            employer=org.get("name"),
            title=person.get("title"),
            seniority=person.get("seniority"),
            departments=person.get("departments") or [],
            raw=person,
            provider=self.name,
        )
