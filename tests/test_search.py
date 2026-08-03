"""Tests for keyword/semantic/hybrid search and filtering."""

from __future__ import annotations

import pytest

from backend.models.receipt import LineItem, Merchant, Receipt
from backend.schemas.api import SearchQuery
from backend.search.hybrid import reciprocal_rank_fusion
from backend.search.keyword_search import keyword_search
from backend.services.search_service import SearchService
from tests.conftest import FakeEmbeddingProvider


def _seed_coffee_shop(db):
    merchant = Merchant(name="Corner Cafe")
    db.add(merchant)
    db.flush()
    receipt = Receipt(
        merchant_id=merchant.id,
        merchant_name="Corner Cafe",
        total=9.5,
        image_path="/tmp/x.png",
        image_hash="h1",
        status="processed",
    )
    receipt.line_items.append(LineItem(name="Espresso", quantity=1, total_price=3.5, category="beverages"))
    receipt.line_items.append(
        LineItem(name="Blueberry Muffin", quantity=1, total_price=6.0, category="snacks")
    )
    db.add(receipt)
    db.commit()
    return receipt


def test_keyword_search_finds_exact_and_substring_matches(db_session_factory):
    with db_session_factory() as db:
        _seed_coffee_shop(db)
        results = keyword_search(db, "espresso", limit=10)
        assert any(item.name == "Espresso" for item, _receipt, _score in results)


def test_keyword_search_matches_category(db_session_factory):
    with db_session_factory() as db:
        _seed_coffee_shop(db)
        results = keyword_search(db, "snacks", limit=10)
        assert any(item.name == "Blueberry Muffin" for item, _r, _s in results)


def test_reciprocal_rank_fusion_favors_items_ranked_highly_in_both_lists():
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]])
    assert fused["a"] >= fused["c"]
    assert fused["b"] >= fused["d"]


@pytest.mark.asyncio
async def test_semantic_search_returns_grouped_receipt_results(db_session_factory):
    with db_session_factory() as db:
        receipt = _seed_coffee_shop(db)
        provider = FakeEmbeddingProvider()

        from backend.search.vector_store import upsert_embedding

        for item in receipt.line_items:
            text = f"{item.name} | category: {item.category} | purchased at {receipt.merchant_name}"
            vector = provider._embed_one(text)
            upsert_embedding(db, item.id, vector)
        db.commit()

        service = SearchService(db, provider)
        results = await service.search(SearchQuery(query="espresso", mode="semantic", limit=10))
        assert len(results) >= 1
        assert results[0].receipt_id == receipt.id


@pytest.mark.asyncio
async def test_search_respects_merchant_filter(db_session_factory):
    with db_session_factory() as db:
        receipt = _seed_coffee_shop(db)
        provider = FakeEmbeddingProvider()

        from backend.search.vector_store import upsert_embedding

        for item in receipt.line_items:
            upsert_embedding(db, item.id, provider._embed_one(item.name))
        db.commit()

        service = SearchService(db, provider)
        results = await service.search(
            SearchQuery(query="espresso", mode="keyword", merchant="Nonexistent Cafe", limit=10)
        )
        assert results == []


@pytest.mark.asyncio
async def test_search_respects_price_filter(db_session_factory):
    with db_session_factory() as db:
        _seed_coffee_shop(db)
        service = SearchService(db, FakeEmbeddingProvider())
        results = await service.search(SearchQuery(query="espresso", mode="keyword", min_price=100, limit=10))
        assert results == []
