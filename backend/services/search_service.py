"""Orchestrates semantic / keyword / hybrid search and groups matches by receipt."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.embeddings.base import EmbeddingProvider
from backend.models.receipt import LineItem, Receipt
from backend.schemas.api import MatchedItem, SearchQuery, SearchResultItem
from backend.search.hybrid import reciprocal_rank_fusion
from backend.search.keyword_search import keyword_search
from backend.search.vector_store import knn_search
from backend.utils.exceptions import InvalidSearchQueryError

# Over-fetch candidates before applying SQL filters, since filters are applied
# after the vector/keyword lookup returns line-item-level hits.
_CANDIDATE_MULTIPLIER = 5


class SearchService:
    def __init__(self, db: Session, embedding_provider: EmbeddingProvider) -> None:
        self._db = db
        self._embedding_provider = embedding_provider

    async def search(self, query: SearchQuery) -> list[SearchResultItem]:
        if query.mode == "semantic":
            item_scores = await self._semantic(query)
        elif query.mode == "keyword":
            item_scores = self._keyword(query)
        elif query.mode == "hybrid":
            item_scores = await self._hybrid(query)
        else:
            raise InvalidSearchQueryError(f"Unknown search mode: {query.mode}")

        return self._group_by_receipt(item_scores, query)

    async def _semantic(self, query: SearchQuery) -> dict[str, float]:
        query_vector = await self._embedding_provider.embed_query(query.query)
        k = query.limit * _CANDIDATE_MULTIPLIER
        matches = knn_search(self._db, query_vector, k)
        # cosine distance in [0, 2] -> similarity in [0, 1] (0 distance = identical)
        return {item_id: max(0.0, 1.0 - distance / 2.0) for item_id, distance in matches}

    def _keyword(self, query: SearchQuery) -> dict[str, float]:
        results = keyword_search(self._db, query.query, query.limit * _CANDIDATE_MULTIPLIER)
        return {item.id: score for item, _receipt, score in results}

    async def _hybrid(self, query: SearchQuery) -> dict[str, float]:
        semantic_scores = await self._semantic(query)
        keyword_scores = self._keyword(query)

        semantic_ranked = sorted(semantic_scores, key=lambda k: semantic_scores[k], reverse=True)
        keyword_ranked = sorted(keyword_scores, key=lambda k: keyword_scores[k], reverse=True)

        fused = reciprocal_rank_fusion([semantic_ranked, keyword_ranked])
        if fused:
            max_score = max(fused.values())
            fused = {k: v / max_score for k, v in fused.items()}  # normalize to [0, 1]
        return fused

    def _group_by_receipt(self, item_scores: dict[str, float], query: SearchQuery) -> list[SearchResultItem]:
        if not item_scores:
            return []

        rows = self._db.execute(
            select(LineItem, Receipt)
            .join(Receipt, Receipt.id == LineItem.receipt_id)
            .where(LineItem.id.in_(item_scores.keys()))
        ).all()

        grouped: dict[str, list[tuple[LineItem, Receipt]]] = {}
        for item, receipt in rows:
            if not self._passes_filters(receipt, query):
                continue
            grouped.setdefault(receipt.id, []).append((item, receipt))

        results: list[SearchResultItem] = []
        for receipt_id, pairs in grouped.items():
            receipt = pairs[0][1]
            matched = sorted(
                (
                    MatchedItem(
                        line_item_id=item.id,
                        name=item.name,
                        total_price=item.total_price,
                        score=round(item_scores[item.id], 4),
                    )
                    for item, _r in pairs
                ),
                key=lambda m: m.score,
                reverse=True,
            )
            results.append(
                SearchResultItem(
                    receipt_id=receipt_id,
                    merchant_name=receipt.merchant_name,
                    purchase_datetime=receipt.purchase_datetime,
                    total=receipt.total,
                    currency=receipt.currency,
                    matched_items=matched,
                    best_score=matched[0].score,
                )
            )

        results.sort(key=lambda r: r.best_score, reverse=True)
        return results[: query.limit]

    @staticmethod
    def _passes_filters(receipt: Receipt, query: SearchQuery) -> bool:
        if query.merchant and query.merchant.lower() not in receipt.merchant_name.lower():
            return False
        if query.date_from and (
            receipt.purchase_datetime is None or receipt.purchase_datetime.date() < query.date_from
        ):
            return False
        if query.date_to and (
            receipt.purchase_datetime is None or receipt.purchase_datetime.date() > query.date_to
        ):
            return False
        if query.min_price is not None and receipt.total < query.min_price:
            return False
        if query.max_price is not None and receipt.total > query.max_price:
            return False
        return True
