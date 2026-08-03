"""Embedding provider abstraction — mirrors the VisionProvider pattern.

No local ML model is loaded anywhere in this app; embeddings are produced by
calling a hosted API. This keeps the backend container small and fast to
cold-start on Railway/Render, at the cost of a network round-trip per batch.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProviderError(Exception):
    """Raised when an embedding provider fails to produce vectors."""


class EmbeddingProvider(ABC):
    dimensions: int

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, preserving input order."""
        raise NotImplementedError

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single search query. Default: reuse embed_texts."""
        vectors = await self.embed_texts([text])
        return vectors[0]
