"""Evaluate saved ReceiptMind predictions against manually labeled examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.evaluation.metrics import evaluate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="JSON file containing labeled extraction and search cases")
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    print(json.dumps(evaluate_dataset(dataset), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
