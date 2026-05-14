"""Routers for endpoints scheduled for later sprints — return 501 today."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

NOT_YET = "not implemented in this sprint"


def _stub(prefix: str, tag: str) -> APIRouter:
    r = APIRouter(prefix=prefix, tags=[tag])

    @r.get("")
    async def _root() -> dict[str, str]:
        raise HTTPException(501, NOT_YET)

    return r


recompetes_router = _stub("/v1/recompetes", "recompetes")
lcats_router = _stub("/v1/lcats", "lcats")
gaps_router = _stub("/v1/gaps", "gaps")
bench_router = _stub("/v1/bench", "bench")
alerts_router = _stub("/v1/alerts", "alerts")
auth_router = _stub("/v1/auth", "auth")
