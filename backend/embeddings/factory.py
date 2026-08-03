"""Embedding provider factory — same single-registration-point pattern as vision."""

from __future__ import annotations

from functools import lru_cache

from backend.config import Settings
from backend.embeddings.base import EmbeddingProvider, EmbeddingProviderError


@lru_cache
def _build(provider: str, api_key: str, model: str, dimensions: int) -> EmbeddingProvider:
    if provider == "gemini":
        from backend.embeddings.gemini_embeddings import GeminiEmbeddingProvider

        return GeminiEmbeddingProvider(api_key=api_key, model=model, dimensions=dimensions)

    raise EmbeddingProviderError(f"Unknown EMBEDDING_PROVIDER: {provider!r}")


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    return _build(
        provider,
        settings.gemini_api_key,
        settings.gemini_embedding_model,
        settings.embedding_dimensions,
    )
