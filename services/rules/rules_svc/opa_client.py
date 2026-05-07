"""Thin OPA REST client used by the rules service."""

from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

log = structlog.get_logger("rules.opa")


class OpaClient:
    def __init__(self, base_url: str | None = None, *, timeout: float = 5.0) -> None:
        self._base_url = (base_url or os.environ.get("OPA_URL", "http://localhost:8181")).rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def evaluate(
        self,
        package: str,
        rule: str,
        inputs: dict[str, Any],
    ) -> dict[str, Any]:
        path = f"{package.replace('.', '/')}/{rule}"
        url = f"{self._base_url}/v1/data/{path}"
        response = await self._client.post(url, json={"input": inputs})
        if response.status_code >= 400:
            log.error("opa_error", url=url, status=response.status_code, body=response.text[:300])
            raise RuntimeError(f"OPA returned {response.status_code}: {response.text[:200]}")
        body = response.json()
        # OPA wraps the result in {"result": ...}; rules return a dict.
        return body.get("result") or {}

    async def health(self) -> bool:
        try:
            response = await self._client.get(f"{self._base_url}/health?bundle=false")
            return response.status_code == 200
        except httpx.HTTPError:
            return False
