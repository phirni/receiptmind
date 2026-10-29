"""ORM models for merchants, receipts, and line items."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def _uuid() -> str:
    return uuid.uuid4().hex


class Merchant(Base):
    __tablename__ = "merchants"
    __table_args__ = (UniqueConstraint("name", "address", name="uq_merchant_name_address"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    receipts: Mapped[list[Receipt]] = relationship(back_populates="merchant")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    merchant_id: Mapped[str | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Denormalized merchant fields kept for fast display / in case the LLM
    # returns a merchant name that we haven't linked yet.
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    merchant_address: Mapped[str | None] = mapped_column(String(500), nullable=True)

    receipt_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")

    subtotal: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax: Mapped[float | None] = mapped_column(Float, nullable=True)
    total: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)

    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    purchase_datetime: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    # Provenance / QA
    image_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    image_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_extraction: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # raw LLM JSON, for audit/re-index
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="processed", index=True)
    # status: pending | processed | failed | duplicate

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=_utcnow, index=True)

    merchant: Mapped[Merchant | None] = relationship(back_populates="receipts")
    line_items: Mapped[list[LineItem]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (Index("ix_receipts_merchant_date", "merchant_name", "purchase_datetime"),)


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    receipt_id: Mapped[str] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    unit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # 0/1 flag (not a real Boolean column) marking whether this item still
    # needs (re)embedding into the configured vector index.
    is_embedded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    receipt: Mapped[Receipt] = relationship(back_populates="line_items")
