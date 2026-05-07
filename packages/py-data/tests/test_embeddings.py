"""Tests for the deterministic embedding provider."""

from __future__ import annotations

import math

import pytest

from wfi_data.embeddings import DEFAULT_EMBEDDING_DIM, NullEmbeddingProvider


@pytest.mark.asyncio
async def test_null_provider_produces_unit_vectors():
    provider = NullEmbeddingProvider()
    vec = await provider.embed("Cleared Sales Engineer in DC Metro")
    assert len(vec) == DEFAULT_EMBEDDING_DIM
    norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(norm, abs=1e-6) == 1.0


@pytest.mark.asyncio
async def test_similar_strings_have_higher_similarity():
    provider = NullEmbeddingProvider()
    a = await provider.embed("TS/SCI cleared sales engineer Maryland")
    b = await provider.embed("Cleared TS/SCI sales engineer Bethesda Maryland")
    c = await provider.embed("Restaurant manager San Francisco")

    def dot(x: list[float], y: list[float]) -> float:
        return sum(xi * yi for xi, yi in zip(x, y))

    assert dot(a, b) > dot(a, c)


@pytest.mark.asyncio
async def test_embed_many_matches_single():
    provider = NullEmbeddingProvider()
    text = "Hello world"
    single = await provider.embed(text)
    many = await provider.embed_many([text, text])
    assert many[0] == single
    assert many[1] == single


@pytest.mark.asyncio
async def test_embed_handles_short_inputs():
    provider = NullEmbeddingProvider()
    vec = await provider.embed("a")
    assert len(vec) == DEFAULT_EMBEDDING_DIM
