"""Request/response schemas for the public API."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class LineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    quantity: float
    unit_price: float | None
    total_price: float
    category: str | None


class ReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    merchant_name: str
    merchant_address: str | None
    receipt_number: str | None
    currency: str
    subtotal: float | None
    tax: float | None
    total: float
    payment_method: str | None
    purchase_datetime: dt.datetime | None
    confidence: float | None
    status: str
    error_message: str | None
    image_path: str
    created_at: dt.datetime
    line_items: list[LineItemRead] = Field(default_factory=list)


class ReceiptListItem(BaseModel):
    """Slim shape used for the paginated /receipts list."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    merchant_name: str
    total: float
    currency: str
    purchase_datetime: dt.datetime | None
    status: str
    item_count: int = 0


class PaginatedReceipts(BaseModel):
    items: list[ReceiptListItem]
    total: int
    page: int
    page_size: int
    pages: int


class UploadResultItem(BaseModel):
    filename: str
    status: str  # queued | duplicate | rejected
    receipt_id: str | None = None
    detail: str | None = None


class UploadResponse(BaseModel):
    accepted: int
    rejected: int
    results: list[UploadResultItem]


class SearchQuery(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    mode: str = Field(default="hybrid", pattern="^(semantic|keyword|hybrid)$")
    limit: int = Field(default=20, ge=1, le=100)
    merchant: str | None = None
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)


class MatchedItem(BaseModel):
    line_item_id: str
    name: str
    total_price: float
    score: float


class SearchResultItem(BaseModel):
    receipt_id: str
    merchant_name: str
    purchase_datetime: dt.datetime | None
    total: float
    currency: str
    matched_items: list[MatchedItem]
    best_score: float


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: list[SearchResultItem]
    count: int


class StatsResponse(BaseModel):
    total_receipts: int
    total_spent: float
    average_receipt_value: float
    monthly_spending: list[dict]
    merchant_frequency: list[dict]
    category_frequency: list[dict]
    top_purchases: list[dict]


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
