"""Tests for the vision + embedding provider abstraction and retry behavior."""

from __future__ import annotations

import pytest

from backend.providers.base import VisionProviderError
from tests.conftest import FakeEmbeddingProvider, FakeVisionProvider


@pytest.mark.asyncio
async def test_fake_vision_provider_returns_extraction():
    provider = FakeVisionProvider()
    result = await provider.extract_receipt(b"fake-bytes", "image/png")
    assert result.merchant_name == "Test Cafe"
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_fake_vision_provider_raises_on_failure():
    provider = FakeVisionProvider(should_fail=True)
    with pytest.raises(VisionProviderError):
        await provider.extract_receipt(b"fake-bytes", "image/png")


@pytest.mark.asyncio
async def test_embedding_provider_returns_unit_vectors():
    provider = FakeEmbeddingProvider()
    vectors = await provider.embed_texts(["coffee", "latte"])
    assert len(vectors) == 2
    for v in vectors:
        assert len(v) == provider.dimensions
        norm = sum(x * x for x in v) ** 0.5
        assert norm == pytest.approx(1.0, abs=1e-6) or norm == 0.0


@pytest.mark.asyncio
async def test_embedding_provider_preserves_order():
    provider = FakeEmbeddingProvider()
    texts = ["apple", "banana", "cherry"]
    vectors = await provider.embed_texts(texts)
    # Same text embedded alone should match the batched result (deterministic).
    solo = await provider.embed_texts([texts[1]])
    assert vectors[1] == solo[0]


def test_vision_provider_factory_raises_for_unknown_provider():
    from backend.config import Settings
    from backend.providers.factory import get_vision_provider

    settings = Settings(vision_provider="not-a-real-provider", gemini_api_key="x")
    with pytest.raises(VisionProviderError):
        get_vision_provider(settings)
