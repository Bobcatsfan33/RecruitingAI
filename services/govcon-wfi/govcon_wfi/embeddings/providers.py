"""Embedding providers.

The real implementation calls OpenAI (text-embedding-3-small, 1536-dim).
The Null provider produces a deterministic 1536-dim vector via hashing for
unit tests + offline mode — semantic search degrades gracefully but stays
testable.
"""

from __future__ import annotations

import hashlib
import os
import struct
from typing import Protocol


EMBEDDING_DIM = 1536


class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]: ...


def _normalise(vec: list[float]) -> list[float]:
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


class NullEmbeddingProvider:
    """Deterministic hash-based embedding — useful for tests + dev fallback."""

    def __init__(self, dim: int = EMBEDDING_DIM):
        self._dim = dim

    async def embed(self, text: str) -> list[float]:
        # Iteratively hash to fill ``dim`` bytes worth of float bins, then
        # convert to floats and L2-normalise.
        digest = b""
        seed = text.encode("utf-8")
        i = 0
        # Each int → 4 bytes → one float bin. Need dim*4 bytes.
        target_bytes = self._dim * 4
        while len(digest) < target_bytes:
            digest += hashlib.sha256(seed + str(i).encode()).digest()
            i += 1
        floats = [
            (struct.unpack("<i", digest[j * 4 : j * 4 + 4])[0] / 2_147_483_647)
            for j in range(self._dim)
        ]
        return _normalise(floats)


class OpenAIEmbeddingProvider:
    """text-embedding-3-small via the OpenAI HTTP API."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str) -> list[float]:
        import httpx  # noqa: PLC0415

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "input": text[:8000]},
            )
            resp.raise_for_status()
            data = resp.json()
            return list(data["data"][0]["embedding"])


_EMBEDDER: EmbeddingProvider | None = None


def set_embedder_for_tests(provider: EmbeddingProvider) -> None:
    global _EMBEDDER
    _EMBEDDER = provider


def get_embedder() -> EmbeddingProvider:
    global _EMBEDDER
    if _EMBEDDER is not None:
        return _EMBEDDER
    api_key = os.environ.get("OPENAI_API_KEY")
    _EMBEDDER = OpenAIEmbeddingProvider(api_key) if api_key else NullEmbeddingProvider()
    return _EMBEDDER
