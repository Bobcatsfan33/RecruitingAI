"""Embedding providers.

Anthropic does not yet ship a native embeddings endpoint as of this writing,
so production wiring uses Voyage AI (Anthropic's recommended embedding
provider) by default. The interface lets us swap to OpenAI or any other
provider without touching call sites.

For dev / tests we ship :class:`NullEmbeddingProvider` which deterministically
hashes the input into a fixed-dim float vector — semantic search returns
ordering useful for unit tests (lexical similarity ≈ cosine similarity in
the trigram-hash construction below).
"""

from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol

import httpx
import structlog

log = structlog.get_logger("wfi.data.embeddings")

DEFAULT_EMBEDDING_DIM = 1536


class EmbeddingProvider(Protocol):
    @property
    def dim(self) -> int: ...
    async def embed(self, text: str) -> list[float]: ...
    async def embed_many(self, texts: list[str]) -> list[list[float]]: ...


class NullEmbeddingProvider:
    """Deterministic, content-aware embedding for tests + dev.

    Builds the vector from rolling trigram hashes of the input — substrings
    that share trigrams produce vectors with high cosine similarity. Not
    semantically meaningful but adequate for verifying ANN plumbing.
    """

    def __init__(self, dim: int = DEFAULT_EMBEDDING_DIM) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    async def embed(self, text: str) -> list[float]:
        return self._embed(text)

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        cleaned = (text or "").lower()
        if len(cleaned) < 3:
            cleaned = (cleaned + "   ")[:3]
        for i in range(len(cleaned) - 2):
            tri = cleaned[i : i + 3]
            digest = hashlib.blake2b(tri.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "big") % self._dim
            sign = 1 if digest[4] & 1 else -1
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            return vec
        return [x / norm for x in vec]


class AnthropicEmbeddingProvider:
    """Voyage AI provider (Anthropic's recommended embedding partner).

    Set ``VOYAGE_API_KEY``. Default model ``voyage-3`` returns 1024-dim
    vectors; we right-pad to ``DEFAULT_EMBEDDING_DIM`` so the same Postgres
    column shape works regardless of provider switch.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "voyage-3",
        dim: int = DEFAULT_EMBEDDING_DIM,
    ) -> None:
        key = api_key or os.environ.get("VOYAGE_API_KEY")
        if not key:
            raise RuntimeError("VOYAGE_API_KEY required for AnthropicEmbeddingProvider")
        self._key = key
        self._model = model
        self._dim = dim
        self._client = httpx.AsyncClient(
            base_url="https://api.voyageai.com/v1",
            headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
            timeout=30.0,
        )

    @property
    def dim(self) -> int:
        return self._dim

    async def embed(self, text: str) -> list[float]:
        result = await self.embed_many([text])
        return result[0]

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Voyage caps inputs around 8k tokens; truncate aggressively to stay safe.
        normalised = [t[:6000] for t in texts]
        response = await self._client.post(
            "/embeddings",
            json={"input": normalised, "model": self._model, "input_type": "document"},
        )
        response.raise_for_status()
        body = response.json()
        out: list[list[float]] = []
        for record in body["data"]:
            vec = record["embedding"]
            if len(vec) < self._dim:
                vec = vec + [0.0] * (self._dim - len(vec))
            out.append(vec[: self._dim])
        return out
