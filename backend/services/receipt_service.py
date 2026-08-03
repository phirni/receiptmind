"""CRUD operations for receipts, used by the /receipts endpoints."""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.elements import ColumnElement

from backend.models.receipt import LineItem, Receipt
from backend.schemas.api import PaginatedReceipts, ReceiptListItem
from backend.search.vector_store import delete_embedding
from backend.utils.exceptions import ReceiptNotFoundError


class ReceiptService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, receipt_id: str) -> Receipt:
        receipt = self._db.execute(
            select(Receipt).options(selectinload(Receipt.line_items)).where(Receipt.id == receipt_id)
        ).scalar_one_or_none()
        if receipt is None:
            raise ReceiptNotFoundError(f"Receipt {receipt_id} not found.")
        return receipt

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        merchant: str | None = None,
        date_from: dt.date | None = None,
        date_to: dt.date | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> PaginatedReceipts:
        stmt = select(Receipt)
        count_stmt = select(func.count()).select_from(Receipt)

        conditions: list[ColumnElement[bool]] = []
        if merchant:
            conditions.append(Receipt.merchant_name.ilike(f"%{merchant}%"))
        if date_from:
            conditions.append(Receipt.purchase_datetime >= dt.datetime.combine(date_from, dt.time.min))
        if date_to:
            conditions.append(Receipt.purchase_datetime <= dt.datetime.combine(date_to, dt.time.max))
        if min_price is not None:
            conditions.append(Receipt.total >= min_price)
        if max_price is not None:
            conditions.append(Receipt.total <= max_price)

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        sort_column = {
            "created_at": Receipt.created_at,
            "total": Receipt.total,
            "purchase_datetime": Receipt.purchase_datetime,
            "merchant_name": Receipt.merchant_name,
        }.get(sort_by, Receipt.created_at)
        stmt = stmt.order_by(sort_column.desc() if sort_dir == "desc" else sort_column.asc())

        total = self._db.execute(count_stmt).scalar_one()
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        receipts = self._db.execute(stmt).scalars().all()

        items = [
            ReceiptListItem(
                id=r.id,
                merchant_name=r.merchant_name,
                total=r.total,
                currency=r.currency,
                purchase_datetime=r.purchase_datetime,
                status=r.status,
                item_count=len(r.line_items) if r.line_items else self._count_items(r.id),
            )
            for r in receipts
        ]
        pages = max(1, math.ceil(total / page_size))
        return PaginatedReceipts(items=items, total=total, page=page, page_size=page_size, pages=pages)

    def _count_items(self, receipt_id: str) -> int:
        return self._db.execute(
            select(func.count()).select_from(LineItem).where(LineItem.receipt_id == receipt_id)
        ).scalar_one()

    def delete(self, receipt_id: str) -> None:
        receipt = self.get(receipt_id)
        for item in receipt.line_items:
            delete_embedding(self._db, item.id)
        image_path = Path(receipt.image_path)
        self._db.delete(receipt)
        self._db.commit()
        if image_path.exists():
            image_path.unlink(missing_ok=True)
