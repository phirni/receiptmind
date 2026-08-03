"""Gemini embedding API implementation of EmbeddingProvider."""

from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import types

from backend.embeddings.base import EmbeddingProvider, EmbeddingProviderError

logger = logging.getLogger(__name__)

# The API accepts many texts per call, but we chunk conservatively to keep
# individual requests fast and retries cheap.
_BATCH_SIZE = 32
_MAX_RETRIES = 3


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dimensions: int) -> None:
        if not api_key:
            raise EmbeddingProviderError("GEMINI_API_KEY is not configured.")
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            results.extend(await self._embed_batch(batch, task_type="RETRIEVAL_DOCUMENT"))
        return results

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed_batch([text], task_type="RETRIEVAL_QUERY")
        return vectors[0]

    async def _embed_batch(self, batch: list[str], task_type: str) -> list[list[float]]:
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                return await asyncio.to_thread(self._sync_embed, batch, task_type)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Embedding batch attempt %d failed: %s", attempt + 1, exc)
                await asyncio.sleep(min(2**attempt, 8))
        raise EmbeddingProviderError(f"Embedding failed after retries: {last_error}") from last_error

    def _sync_embed(self, batch: list[str], task_type: str) -> list[list[float]]:
        response = self._client.models.embed_content(
            model=self._model,
            contents=batch,  # type: ignore[arg-type]
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.dimensions,
            ),
        )
        if not response.embeddings:
            raise EmbeddingProviderError("Gemini returned no embeddings for this batch.")
        return [list(e.values or []) for e in response.embeddings]
