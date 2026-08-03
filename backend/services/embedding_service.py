"""Keeps the sqlite-vec index in sync with line_items."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.embeddings.base import EmbeddingProvider
from backend.models.receipt import LineItem, Receipt
from backend.search.vector_store import upsert_embedding

logger = logging.getLogger(__name__)


def _embedding_text(item: LineItem, merchant_name: str) -> str:
    """Compose the text we embed for a line item.

    Including merchant + category alongside the raw item name helps queries
    like "things I bought at the airport" or "snacks" match even when the
    item name alone is terse (e.g. "SNCK BAR 1.5OZ").
    """
    parts = [item.name]
    if item.category:
        parts.append(f"category: {item.category}")
    parts.append(f"purchased at {merchant_name}")
    return " | ".join(parts)


class EmbeddingService:
    def __init__(self, db: Session, provider: EmbeddingProvider) -> None:
        self._db = db
        self._provider = provider

    async def embed_receipt(self, receipt: Receipt) -> None:
        """Embed every line item on a freshly-processed receipt."""
        if not receipt.line_items:
            return
        texts = [_embedding_text(li, receipt.merchant_name) for li in receipt.line_items]
        vectors = await self._provider.embed_texts(texts)
        for item, vector in zip(receipt.line_items, vectors, strict=True):
            upsert_embedding(self._db, item.id, vector)
            item.is_embedded = 1
        self._db.commit()
        logger.info("Embedded %d line items for receipt %s", len(texts), receipt.id)

    async def reindex_all(self, batch_size: int = 64) -> int:
        """Re-embed every line item in the database. Used by POST /reindex."""
        items = self._db.execute(
            select(LineItem, Receipt.merchant_name).join(Receipt, Receipt.id == LineItem.receipt_id)
        ).all()

        total = 0
        for start in range(0, len(items), batch_size):
            batch = items[start : start + batch_size]
            texts = [_embedding_text(li, merchant_name) for li, merchant_name in batch]
            vectors = await self._provider.embed_texts(texts)
            for (li, _merchant_name), vector in zip(batch, vectors, strict=True):
                upsert_embedding(self._db, li.id, vector)
                li.is_embedded = 1
            self._db.commit()
            total += len(batch)
        logger.info("Reindexed %d line items", total)
        return total
