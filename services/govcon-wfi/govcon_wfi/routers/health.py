"""Liveness + readiness."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "live"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    return {"status": "ready"}
