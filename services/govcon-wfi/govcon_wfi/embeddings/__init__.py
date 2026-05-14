"""Text embedding providers (mock + real)."""

from govcon_wfi.embeddings.providers import (
    EmbeddingProvider,
    NullEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedder,
    set_embedder_for_tests,
)

__all__ = [
    "EmbeddingProvider",
    "NullEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "get_embedder",
    "set_embedder_for_tests",
]
