"""ATS adapters.

Greenhouse Harvest API has a free developer tier (basic auth with an API
key generated from a personal sandbox account). iCIMS requires an
enterprise contract — interface only.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
import structlog

log = structlog.get_logger("pipeline.ats")


@dataclass
class AtsSubmission:
    candidate_email: str
    candidate_first_name: str
    candidate_last_name: str
    job_id: str  # external ATS job id
    source: str = "Workforce Intelligence"
    notes: str = ""


@dataclass
class AtsSubmissionResult:
    success: bool
    provider: str
    external_id: str | None = None
    url: str | None = None
    error: str | None = None


class AtsAdapter(Protocol):
    name: str
    async def submit(self, submission: AtsSubmission) -> AtsSubmissionResult: ...
    async def fetch_status(self, external_id: str) -> dict[str, Any]: ...


class GreenhouseAdapter:
    """Greenhouse Harvest API. Uses Basic auth with an API key as username
    and an empty password. Free developer accounts are available."""

    name = "greenhouse"
    BASE = "https://harvest.greenhouse.io/v1"

    def __init__(self, *, api_key: str | None = None, on_behalf_of: str | None = None) -> None:
        key = api_key or os.environ.get("GREENHOUSE_HARVEST_API_KEY")
        if not key:
            raise RuntimeError("GREENHOUSE_HARVEST_API_KEY is required")
        token = base64.b64encode(f"{key}:".encode()).decode()
        headers = {
            "Authorization": f"Basic {token}",
            "content-type": "application/json",
        }
        if on_behalf_of:
            headers["On-Behalf-Of"] = on_behalf_of
        self._client = httpx.AsyncClient(base_url=self.BASE, headers=headers, timeout=15.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def submit(self, submission: AtsSubmission) -> AtsSubmissionResult:
        # Greenhouse: POST /candidates with applications=[{job_id}]
        payload = {
            "first_name": submission.candidate_first_name,
            "last_name": submission.candidate_last_name,
            "email_addresses": [{"value": submission.candidate_email, "type": "personal"}],
            "applications": [
                {"job_id": int(submission.job_id), "source_id": None}
            ],
            "notes": submission.notes,
        }
        try:
            response = await self._client.post("/candidates", json=payload)
        except httpx.HTTPError as exc:
            return AtsSubmissionResult(success=False, provider=self.name, error=str(exc))
        if response.status_code in (200, 201):
            body = response.json()
            return AtsSubmissionResult(
                success=True,
                provider=self.name,
                external_id=str(body.get("id")),
                url=f"https://app.greenhouse.io/people/{body.get('id')}",
            )
        return AtsSubmissionResult(
            success=False, provider=self.name, error=response.text[:200]
        )

    async def fetch_status(self, external_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/candidates/{external_id}")
        if response.status_code != 200:
            return {"error": response.text[:200]}
        return response.json()


class MockAtsAdapter:
    """Captures submissions in-memory. Default when no real credentials."""

    def __init__(self, name: str = "mock") -> None:
        self.name = name
        self.submissions: list[AtsSubmission] = []
        self._next_id = 1

    async def submit(self, submission: AtsSubmission) -> AtsSubmissionResult:
        self.submissions.append(submission)
        external = f"mock-{self._next_id}"
        self._next_id += 1
        return AtsSubmissionResult(
            success=True, provider=self.name, external_id=external,
            url=f"https://mock-ats.local/candidates/{external}",
        )

    async def fetch_status(self, external_id: str) -> dict[str, Any]:
        return {"id": external_id, "status": "in_review", "stage": "screen"}


def select_adapter() -> AtsAdapter:
    if os.environ.get("GREENHOUSE_HARVEST_API_KEY"):
        try:
            return GreenhouseAdapter()
        except RuntimeError as exc:
            log.warning("greenhouse_init_failed", error=str(exc))
    return MockAtsAdapter()
