"""Data layer: resume parsing, enrichment adapters, embeddings."""

from wfi_data.embeddings import (
    EmbeddingProvider,
    NullEmbeddingProvider,
    AnthropicEmbeddingProvider,
    DEFAULT_EMBEDDING_DIM,
)
from wfi_data.enrichment import (
    EnrichmentAdapter,
    EnrichmentResult,
    MockEnrichmentAdapter,
    ApolloEnrichmentAdapter,
)
from wfi_data.resume import (
    ParsedResume,
    ResumeParser,
    parse_pdf_bytes,
    parse_docx_bytes,
    extract_text_from_bytes,
)

__all__ = [
    "AnthropicEmbeddingProvider",
    "ApolloEnrichmentAdapter",
    "DEFAULT_EMBEDDING_DIM",
    "EmbeddingProvider",
    "EnrichmentAdapter",
    "EnrichmentResult",
    "MockEnrichmentAdapter",
    "NullEmbeddingProvider",
    "ParsedResume",
    "ResumeParser",
    "extract_text_from_bytes",
    "parse_docx_bytes",
    "parse_pdf_bytes",
]
