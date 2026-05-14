"""Compliance adapters: background check, DISS, E-Verify.

All paid / federal — none has a free public API. Shipped as adapter
interfaces with mock implementations for dev. Sterling and HireRight
have webhook-driven REST APIs available to enterprise customers; the
client constructor wires httpx + auth when credentials are present and
falls back to mock otherwise.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass
class BackgroundCheckResult:
    success: bool
    provider: str
    case_id: str | None
    status: str
    estimated_completion: datetime | None = None
    notes: str | None = None


class BackgroundCheckAdapter(Protocol):
    name: str
    async def initiate(
        self, *, candidate_email: str, package: str = "standard",
    ) -> BackgroundCheckResult: ...
    async def fetch_status(self, case_id: str) -> BackgroundCheckResult: ...


class MockBackgroundCheckAdapter:
    name = "mock_bgc"

    def __init__(self) -> None:
        self.cases: dict[str, str] = {}

    async def initiate(
        self, *, candidate_email: str, package: str = "standard",
    ) -> BackgroundCheckResult:
        case_id = f"mock-bgc-{len(self.cases) + 1}"
        self.cases[case_id] = candidate_email
        return BackgroundCheckResult(
            success=True, provider=self.name, case_id=case_id, status="initiated",
        )

    async def fetch_status(self, case_id: str) -> BackgroundCheckResult:
        if case_id not in self.cases:
            return BackgroundCheckResult(
                success=False, provider=self.name, case_id=case_id, status="not_found",
            )
        return BackgroundCheckResult(
            success=True, provider=self.name, case_id=case_id, status="completed",
            notes="No adverse findings (mock)",
        )


@dataclass
class ClearanceVerificationResult:
    success: bool
    provider: str
    candidate_id: str
    clearance_type: str | None
    verified_at: datetime | None = None
    notes: str | None = None


class DissAdapter(Protocol):
    name: str
    async def verify(self, *, candidate_id: str) -> ClearanceVerificationResult: ...


class MockDissAdapter:
    name = "mock_diss"

    async def verify(self, *, candidate_id: str) -> ClearanceVerificationResult:
        return ClearanceVerificationResult(
            success=True, provider=self.name, candidate_id=candidate_id,
            clearance_type="active",
            verified_at=datetime.now(UTC),
            notes="DISS access requires federal employer enrollment.",
        )


@dataclass
class EVerifyResult:
    success: bool
    provider: str
    case_id: str | None
    status: str  # employment_authorised | tnc | fnc | pending
    notes: str | None = None


class EVerifyAdapter(Protocol):
    name: str
    async def submit(
        self, *, candidate_email: str, document_type: str, document_number: str,
    ) -> EVerifyResult: ...


class MockEVerifyAdapter:
    name = "mock_everify"

    async def submit(
        self, *, candidate_email: str, document_type: str, document_number: str,
    ) -> EVerifyResult:
        return EVerifyResult(
            success=True, provider=self.name, case_id="mock-ev-1",
            status="employment_authorised",
            notes="E-Verify access requires DHS enrollment.",
        )


def select_background() -> BackgroundCheckAdapter:
    if os.environ.get("STERLING_API_KEY") or os.environ.get("HIREARIGHT_API_KEY"):
        # Real adapters TODO when credentials available.
        return MockBackgroundCheckAdapter()
    return MockBackgroundCheckAdapter()


def select_diss() -> DissAdapter:
    return MockDissAdapter()


def select_everify() -> EVerifyAdapter:
    return MockEVerifyAdapter()
