"""Simple substring/keyword search, used standalone and as one signal in hybrid search."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models.receipt import LineItem, Receipt


def keyword_search(db: Session, query: str, limit: int) -> list[tuple[LineItem, Receipt, float]]:
    """Return (line_item, receipt, score) tuples, best matches first.

    Score is a crude but transparent relevance signal: exact (case-insensitive)
    name match scores highest, substring match scores lower, and matches on
    merchant name or category score lowest. This exists mainly so keyword
    search still works usefully if the embedding API is ever unavailable, and
    to give hybrid search a non-semantic signal for exact brand/product names.
    """
    like_pattern = f"%{query.lower()}%"
    rows = db.execute(
        select(LineItem, Receipt)
        .join(Receipt, Receipt.id == LineItem.receipt_id)
        .where(
            or_(
                LineItem.name.ilike(like_pattern),
                LineItem.category.ilike(like_pattern),
                Receipt.merchant_name.ilike(like_pattern),
            )
        )
        .limit(limit * 5)
    ).all()

    scored: list[tuple[LineItem, Receipt, float]] = []
    q = query.lower().strip()
    for item, receipt in rows:
        name = item.name.lower()
        if name == q:
            score = 1.0
        elif q in name:
            score = 0.8
        elif item.category and q in item.category.lower():
            score = 0.5
        elif q in receipt.merchant_name.lower():
            score = 0.4
        else:
            score = 0.3
        scored.append((item, receipt, score))

    scored.sort(key=lambda t: t[2], reverse=True)
    return scored[:limit]
