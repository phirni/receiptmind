from __future__ import annotations

import pytest

from backend.evaluation.metrics import evaluate_dataset, evaluate_extraction, evaluate_search, quality_band


def test_extraction_metrics_match_normalized_items_and_amount_tolerance():
    result = evaluate_extraction(
        {"merchant_name": "Blue Bottle", "currency": "USD", "total": 15.81,
         "line_items": [{"name": "Oat Milk Latte"}, {"name": "Croissant"}]},
        {"merchant_name": "  BLUE   BOTTLE ", "currency": "usd", "total": 15.815,
         "line_items": [{"name": "Oat-milk latte"}, {"name": "Tea"}]},
    )

    assert result["field_accuracy"] == 1.0
    assert result["total_within_tolerance"] is True
    assert result["line_items"] == {"precision": 0.5, "recall": 0.5, "f1": 0.5}


def test_search_metrics_reflect_rank_and_recall():
    result = evaluate_search(["irrelevant", "relevant-a", "relevant-b"], ["relevant-a", "relevant-b"], k=3)

    assert result["recall@3"] == 1.0
    assert result["mrr"] == 0.5
    assert 0 < result["ndcg@3"] < 1


def test_search_rejects_unlabeled_queries():
    with pytest.raises(ValueError, match="at least one relevant item"):
        evaluate_search(["item"], [], k=5)


def test_dataset_report_includes_qualitative_bands():
    report = evaluate_dataset(
        {
            "k": 2,
            "extraction_cases": [
                {
                    "expected": {"merchant_name": "Shop", "currency": "USD", "total": 2.0,
                                 "line_items": [{"name": "Tea"}]},
                    "predicted": {"merchant_name": "Shop", "currency": "USD", "total": 2.0,
                                  "line_items": [{"name": "Tea"}]},
                }
            ],
            "retrieval_cases": [
                {"ranked_item_ids": ["good"], "relevant_item_ids": ["good"]}
            ],
        }
    )

    assert report["extraction"]["qualitative"] == {"fields": "strong", "line_items": "strong"}
    assert report["retrieval"]["qualitative"] == "strong"
    assert quality_band(0.75) == "promising"
