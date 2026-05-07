"""ATS adapter tests — mock + Greenhouse via respx."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from pipeline_svc.ats import (
    AtsSubmission,
    GreenhouseAdapter,
    MockAtsAdapter,
    select_adapter,
)


@pytest.mark.asyncio
async def test_mock_returns_synthetic_external_id():
    adapter = MockAtsAdapter()
    sub = AtsSubmission(
        candidate_email="a@b.local",
        candidate_first_name="A",
        candidate_last_name="B",
        job_id="123",
    )
    out = await adapter.submit(sub)
    assert out.success
    assert out.external_id and out.external_id.startswith("mock-")
    assert "mock-ats.local" in out.url


@pytest.mark.asyncio
async def test_greenhouse_real_call_via_respx(monkeypatch):
    monkeypatch.setenv("GREENHOUSE_HARVEST_API_KEY", "fake_key")
    async with respx.mock(base_url="https://harvest.greenhouse.io/v1") as router:
        router.post("/candidates").mock(
            return_value=Response(201, json={"id": 999})
        )
        adapter = GreenhouseAdapter()
        out = await adapter.submit(
            AtsSubmission(
                candidate_email="alice@example.com",
                candidate_first_name="Alice",
                candidate_last_name="Smith",
                job_id="42",
            )
        )
        await adapter.aclose()
    assert out.success
    assert out.external_id == "999"


def test_select_adapter_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("GREENHOUSE_HARVEST_API_KEY", raising=False)
    adapter = select_adapter()
    assert isinstance(adapter, MockAtsAdapter)
