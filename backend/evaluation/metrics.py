"""Extraction and retrieval metrics for labeled ReceiptMind benchmark cases."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any


def _normalize_text(value: Any) -> str:
    return " ".join(re.findall(r"\w+", str(value or "").casefold()))


def _item_counts(receipt: Mapping[str, Any]) -> Counter[str]:
    return Counter(
        name
        for item in receipt.get("line_items", [])
        if (name := _normalize_text(item.get("name")))
    )


def _precision_recall_f1(true_positive: int, false_positive: int, false_negative: int) -> dict[str, float]:
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate_extraction(
    expected: Mapping[str, Any], predicted: Mapping[str, Any], *, amount_tolerance: float = 0.01
) -> dict[str, Any]:
    """Compare one model extraction with its verified receipt transcription."""
    exact_fields = {
        "merchant_name": _normalize_text(expected.get("merchant_name"))
        == _normalize_text(predicted.get("merchant_name")),
        "currency": _normalize_text(expected.get("currency", "USD"))
        == _normalize_text(predicted.get("currency", "USD")),
    }
    expected_total = float(expected["total"])
    predicted_total = float(predicted["total"])
    total_error = abs(expected_total - predicted_total)
    item_expected = _item_counts(expected)
    item_predicted = _item_counts(predicted)
    item_tp = sum((item_expected & item_predicted).values())
    item_fp = sum((item_predicted - item_expected).values())
    item_fn = sum((item_expected - item_predicted).values())

    return {
        "field_exact_match": exact_fields,
        "field_accuracy": sum(exact_fields.values()) / len(exact_fields),
        "total_absolute_error": total_error,
        "total_within_tolerance": total_error <= amount_tolerance,
        "line_items": _precision_recall_f1(item_tp, item_fp, item_fn),
        "line_item_counts": {
            "true_positive": item_tp,
            "false_positive": item_fp,
            "false_negative": item_fn,
        },
    }


def evaluate_search(
    ranked_item_ids: Sequence[str], relevant_item_ids: Sequence[str], *, k: int = 5
) -> dict[str, float]:
    """Compute standard top-k metrics for one relevance-labeled search query."""
    if k < 1:
        raise ValueError("k must be at least 1")
    relevant = set(relevant_item_ids)
    if not relevant:
        raise ValueError("each retrieval benchmark query needs at least one relevant item")

    top_k = list(ranked_item_ids[:k])
    hits = [1 if item_id in relevant else 0 for item_id in top_k]
    recall = len(set(top_k) & relevant) / len(relevant)
    reciprocal_rank = next((1.0 / rank for rank, hit in enumerate(hits, start=1) if hit), 0.0)
    dcg = sum(hit / math.log2(rank + 1) for rank, hit in enumerate(hits, start=1))
    ideal_hits = min(len(relevant), k)
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))

    return {
        f"recall@{k}": recall,
        "mrr": reciprocal_rank,
        f"ndcg@{k}": dcg / ideal_dcg if ideal_dcg else 0.0,
    }


def quality_band(score: float) -> str:
    """Give a compact qualitative label for a normalized metric score."""
    if score >= 0.9:
        return "strong"
    if score >= 0.7:
        return "promising"
    return "needs improvement"


def evaluate_dataset(dataset: Mapping[str, Any]) -> dict[str, Any]:
    """Aggregate labeled extraction and retrieval cases into a report."""
    extraction_cases = dataset.get("extraction_cases", [])
    retrieval_cases = dataset.get("retrieval_cases", [])
    k = int(dataset.get("k", 5))

    extraction_results = [
        evaluate_extraction(case["expected"], case["predicted"])
        for case in extraction_cases
    ]
    retrieval_results = [
        evaluate_search(case["ranked_item_ids"], case["relevant_item_ids"], k=k)
        for case in retrieval_cases
    ]

    report: dict[str, Any] = {
        "extraction_cases": len(extraction_results),
        "retrieval_queries": len(retrieval_results),
        "k": k,
    }
    if extraction_results:
        field_accuracy = (
            sum(result["field_accuracy"] for result in extraction_results) / len(extraction_results)
        )
        item_counts = {
            key: sum(result["line_item_counts"][key] for result in extraction_results)
            for key in ("true_positive", "false_positive", "false_negative")
        }
        item_metrics = _precision_recall_f1(
            item_counts["true_positive"], item_counts["false_positive"], item_counts["false_negative"]
        )
        report["extraction"] = {
            "field_accuracy": field_accuracy,
            "total_exact_rate": sum(result["total_within_tolerance"] for result in extraction_results)
            / len(extraction_results),
            "mean_total_absolute_error": sum(result["total_absolute_error"] for result in extraction_results)
            / len(extraction_results),
            "line_items_micro": item_metrics,
            "qualitative": {
                "fields": quality_band(field_accuracy),
                "line_items": quality_band(item_metrics["f1"]),
            },
        }
    if retrieval_results:
        recall_key = f"recall@{k}"
        ndcg_key = f"ndcg@{k}"
        recall = sum(result[recall_key] for result in retrieval_results) / len(retrieval_results)
        mrr = sum(result["mrr"] for result in retrieval_results) / len(retrieval_results)
        ndcg = sum(result[ndcg_key] for result in retrieval_results) / len(retrieval_results)
        report["retrieval"] = {
            recall_key: recall,
            "mrr": mrr,
            ndcg_key: ndcg,
            "qualitative": quality_band(ndcg),
        }
    return report
