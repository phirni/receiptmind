"""Schemas describing the structured output we require from a VisionProvider.

These are intentionally strict: the LLM's raw text is never trusted directly.
It must parse into `ExtractedReceipt` or the extraction is retried / rejected.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field, field_validator, model_validator


class ExtractedLineItem(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    
    quantity: float = Field(default=1.0, gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    total_price: float = Field(ge=0)
    category: str | None = Field(default=None, max_length=100)

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        return " ".join(v.split())


class ExtractedReceipt(BaseModel):
    """Strict schema the vision model's JSON must conform to."""

    merchant_name: str = Field(min_length=1, max_length=255)
    merchant_address: str | None = None
    receipt_number: str | None = None
    currency: str = Field(default="USD", max_length=8)

    subtotal: float | None = Field(default=None, ge=0)
    tax: float | None = Field(default=None, ge=0)
    total: float = Field(ge=0)

    payment_method: str | None = None
    purchase_datetime: dt.datetime | None = None

    line_items: list[ExtractedLineItem] = Field(default_factory=list)

    # 0-1 self-reported confidence from the model, used to flag receipts for
    # manual review; defaults conservatively low if the model omits it.
    confidence: float = Field(default=0.5, ge=0, le=1)

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, v: str) -> str:
        return v.upper().strip() or "USD"

    @model_validator(mode="after")
    def _sanity_check_totals(self) -> ExtractedReceipt:
        """Flag (but do not reject) receipts whose arithmetic doesn't add up.

        Real receipts often have rounding, discounts, or missing tax lines
        that make strict equality wrong to enforce here — we lower the
        confidence instead of raising, and let downstream review handle it.
        """
        if self.subtotal is not None and self.tax is not None:
            expected = round(self.subtotal + self.tax, 2)
            if abs(expected - round(self.total, 2)) > 0.05:
                self.confidence = min(self.confidence, 0.4)
        return self


EXTRACTION_JSON_SCHEMA = ExtractedReceipt.model_json_schema()
