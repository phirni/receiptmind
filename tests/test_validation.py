"""Tests for the strict Pydantic schema that gates all LLM output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.schemas.extraction import ExtractedReceipt

FIXTURE = Path(__file__).parent / "fixtures" / "sample_receipt_extraction.json"


def test_parses_valid_sample_fixture():
    data = json.loads(FIXTURE.read_text())
    receipt = ExtractedReceipt.model_validate(data)
    assert receipt.merchant_name == "Blue Bottle Coffee"
    assert len(receipt.line_items) == 3
    assert receipt.total == pytest.approx(15.81)


def test_rejects_missing_total():
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate({"merchant_name": "Test"})


def test_rejects_negative_total():
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate({"merchant_name": "Test", "total": -5.0})


def test_rejects_empty_merchant_name():
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate({"merchant_name": "", "total": 5.0})


def test_lowers_confidence_when_arithmetic_is_inconsistent():
    receipt = ExtractedReceipt.model_validate(
        {"merchant_name": "Test", "subtotal": 10.0, "tax": 1.0, "total": 50.0, "confidence": 0.9}
    )
    assert receipt.confidence <= 0.4


def test_keeps_confidence_when_arithmetic_is_consistent():
    receipt = ExtractedReceipt.model_validate(
        {"merchant_name": "Test", "subtotal": 10.0, "tax": 1.0, "total": 11.0, "confidence": 0.9}
    )
    assert receipt.confidence == 0.9


def test_currency_is_uppercased():
    receipt = ExtractedReceipt.model_validate({"merchant_name": "Test", "total": 5.0, "currency": "usd"})
    assert receipt.currency == "USD"


def test_line_item_name_whitespace_is_normalized():
    receipt = ExtractedReceipt.model_validate(
        {
            "merchant_name": "Test",
            "total": 5.0,
            "line_items": [{"name": "  Latte   Grande ", "total_price": 5.0}],
        }
    )
    assert receipt.line_items[0].name == "Latte Grande"


def test_rejects_zero_quantity_line_item():
    with pytest.raises(ValidationError):
        ExtractedReceipt.model_validate(
            {
                "merchant_name": "Test",
                "total": 5.0,
                "line_items": [{"name": "Item", "quantity": 0, "total_price": 5.0}],
            }
        )
