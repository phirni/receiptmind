"""Aggregate queries powering the Statistics page."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.receipt import LineItem, Receipt
from backend.schemas.api import StatsResponse


class StatsService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_stats(self) -> StatsResponse:
        processed = select(Receipt).where(Receipt.status == "processed").subquery()

        total_receipts = self._db.execute(select(func.count()).select_from(processed)).scalar_one()
        total_spent = self._db.execute(select(func.coalesce(func.sum(processed.c.total), 0.0))).scalar_one()
        avg_value = round(total_spent / total_receipts, 2) if total_receipts else 0.0

        month_expr = (
            func.to_char(Receipt.purchase_datetime, "YYYY-MM")
            if self._db.bind is not None and self._db.bind.dialect.name == "postgresql"
            else func.strftime("%Y-%m", Receipt.purchase_datetime)
        )
        monthly = self._db.execute(
            select(
                month_expr.label("month"),
                func.sum(Receipt.total).label("total"),
            )
            .where(Receipt.status == "processed", Receipt.purchase_datetime.is_not(None))
            .group_by("month")
            .order_by("month")
        ).all()

        merchants = self._db.execute(
            select(Receipt.merchant_name, func.count().label("count"), func.sum(Receipt.total).label("total"))
            .where(Receipt.status == "processed")
            .group_by(Receipt.merchant_name)
            .order_by(func.count().desc())
            .limit(10)
        ).all()

        categories = self._db.execute(
            select(LineItem.category, func.count().label("count"))
            .where(LineItem.category.is_not(None))
            .group_by(LineItem.category)
            .order_by(func.count().desc())
            .limit(10)
        ).all()

        top_items = self._db.execute(
            select(LineItem.name, LineItem.total_price, Receipt.merchant_name, Receipt.purchase_datetime)
            .join(Receipt, Receipt.id == LineItem.receipt_id)
            .order_by(LineItem.total_price.desc())
            .limit(10)
        ).all()

        return StatsResponse(
            total_receipts=total_receipts,
            total_spent=round(total_spent, 2),
            average_receipt_value=avg_value,
            monthly_spending=[{"month": m, "total": round(t or 0.0, 2)} for m, t in monthly],
            merchant_frequency=[
                {"merchant": m, "count": c, "total": round(t or 0.0, 2)} for m, c, t in merchants
            ],
            category_frequency=[{"category": c, "count": n} for c, n in categories],
            top_purchases=[
                {"name": n, "price": p, "merchant": m, "date": d.isoformat() if d else None}
                for n, p, m, d in top_items
            ],
        )
