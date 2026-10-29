# ReceiptMind quality benchmarks

`python scripts/evaluate_quality.py path/to/results.json` compares saved model
outputs against manually verified receipt data. It reports merchant/currency
field accuracy, total amount error, line-item precision/recall/F1, and search
Recall@K, MRR, and nDCG@K. The qualitative labels (`strong`, `promising`, or
`needs improvement`) are simple score bands, not claims about business impact.

Use this JSON shape:

```json
{
  "k": 5,
  "extraction_cases": [
    {
      "case_id": "receipt-001",
      "expected": {
        "merchant_name": "Example Market",
        "currency": "USD",
        "total": 12.5,
        "line_items": [{ "name": "Oat Milk" }, { "name": "Apples" }]
      },
      "predicted": {
        "merchant_name": "Example Market",
        "currency": "USD",
        "total": 12.5,
        "line_items": [{ "name": "Oat Milk" }, { "name": "Apples" }]
      }
    }
  ],
  "retrieval_cases": [
    {
      "query": "milk",
      "relevant_item_ids": ["verified-line-item-id"],
      "ranked_item_ids": ["verified-line-item-id", "other-line-item-id"]
    }
  ]
}
```

The example is only a format illustration. Do not use copied expected/predicted
values as model benchmarks; each expected value and relevant search result must
be checked against the original receipt or a human relevance judgment. Keep
separate datasets for tuning and final evaluation.
