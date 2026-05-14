"""OpaClient unit test — mocks the OPA HTTP surface with respx."""

from __future__ import annotations

import pytest
import respx
from httpx import Response
from rules_svc.opa_client import OpaClient


@pytest.mark.asyncio
async def test_evaluate_extracts_result_block():
    async with respx.mock(base_url="http://opa.test:8181") as router:
        router.post("/v1/data/wfi/comp/result").mock(
            return_value=Response(200, json={"result": {"verdict": "feasible", "rule": "comp_market_alignment"}})
        )
        client = OpaClient(base_url="http://opa.test:8181")
        out = await client.evaluate("wfi.comp", "result", {"client_budget": 200000})
        assert out == {"verdict": "feasible", "rule": "comp_market_alignment"}
        await client.aclose()


@pytest.mark.asyncio
async def test_evaluate_raises_on_5xx():
    async with respx.mock(base_url="http://opa.test:8181") as router:
        router.post("/v1/data/wfi/comp/result").mock(return_value=Response(500, text="kaboom"))
        client = OpaClient(base_url="http://opa.test:8181")
        with pytest.raises(RuntimeError):
            await client.evaluate("wfi.comp", "result", {})
        await client.aclose()


@pytest.mark.asyncio
async def test_health_returns_false_on_connect_error():
    client = OpaClient(base_url="http://does-not-exist.invalid:8181", timeout=0.1)
    assert await client.health() is False
    await client.aclose()
