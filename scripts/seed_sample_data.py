"""Seed the database with realistic sample receipts.

This bypasses the vision provider entirely (no API calls, no cost) so you
can explore the Receipts / Statistics pages immediately after cloning. Run
`POST /reindex` afterwards (with a real GEMINI_API_KEY configured) to make
the sample line items searchable via semantic/hybrid search.

Usage:
    uv run python scripts/seed_sample_data.py
"""

from __future__ import annotations

import datetime as dt

from backend.database.init_db import init_db
from backend.database.session import SessionLocal
from backend.models.receipt import LineItem, Merchant, Receipt

SAMPLE_RECEIPTS = [
    {
        "merchant_name": "Blue Bottle Coffee",
        "merchant_address": "300 Webster St, Oakland, CA",
        "total": 15.81,
        "subtotal": 14.50,
        "tax": 1.31,
        "purchase_datetime": dt.datetime(2026, 6, 14, 8, 22),
        "payment_method": "Visa •••• 4471",
        "items": [
            ("Oat Milk Latte", 1, 5.75, "beverages"),
            ("Cold Brew, Large", 1, 4.75, "beverages"),
            ("Almond Croissant", 1, 4.00, "snacks"),
        ],
    },
    {
        "merchant_name": "Whole Foods Market",
        "merchant_address": "1650 Solano Ave, Berkeley, CA",
        "total": 58.42,
        "subtotal": 54.10,
        "tax": 4.32,
        "purchase_datetime": dt.datetime(2026, 6, 12, 18, 5),
        "payment_method": "Mastercard •••• 9021",
        "items": [
            ("Organic Baby Spinach", 1, 4.29, "produce"),
            ("Roma Tomatoes 2lb", 1, 3.98, "produce"),
            ("Whole Milk, 1 Gallon", 1, 5.49, "dairy"),
            ("Greek Yogurt, Plain", 2, 5.98, "dairy"),
            ("Sourdough Bread", 1, 6.49, "bakery"),
            ("Chicken Breast, 2lb", 1, 11.98, "meat"),
            ("Sparkling Water 12pk", 1, 7.99, "beverages"),
            ("Dark Chocolate Bar", 2, 7.98, "snacks"),
        ],
    },
    {
        "merchant_name": "SFO Terminal 2 Marketplace",
        "merchant_address": "San Francisco International Airport",
        "total": 22.75,
        "subtotal": 21.00,
        "tax": 1.75,
        "purchase_datetime": dt.datetime(2026, 5, 28, 6, 40),
        "payment_method": "Amex •••• 1120",
        "items": [
            ("Bottled Water", 1, 4.00, "beverages"),
            ("Trail Mix, Protein", 1, 6.50, "snacks"),
            ("Turkey & Cheese Sandwich", 1, 10.50, "dining"),
        ],
    },
    {
        "merchant_name": "Trader Joe's",
        "merchant_address": "3 Village Ln, Cambridge, MA",
        "total": 31.20,
        "subtotal": 29.00,
        "tax": 2.20,
        "purchase_datetime": dt.datetime(2026, 5, 20, 17, 15),
        "payment_method": "Debit •••• 5588",
        "items": [
            ("Peanut Butter Protein Bars", 1, 5.99, "snacks"),
            ("Frozen Mango Chunks", 1, 3.49, "produce"),
            ("Cold Brew Concentrate", 1, 5.99, "beverages"),
            ("Everything Bagel Seasoning", 1, 2.49, "pantry"),
            ("Unexpected Cheddar", 1, 4.29, "dairy"),
            ("Dark Roast Espresso Beans", 1, 7.99, "beverages"),
        ],
    },
    {
        "merchant_name": "Philz Coffee",
        "merchant_address": "3101 24th St, San Francisco, CA",
        "total": 6.85,
        "subtotal": 6.35,
        "tax": 0.50,
        "purchase_datetime": dt.datetime(2026, 5, 10, 9, 0),
        "payment_method": "Apple Pay",
        "items": [
            ("Mint Mojito Iced Coffee", 1, 6.35, "beverages"),
        ],
    },
]


def seed() -> None:
    init_db()
    with SessionLocal() as db:
        if db.query(Receipt).count() > 0:
            print("Database already has receipts — skipping seed (delete data/receiptmind.db to reset).")
            return

        for r in SAMPLE_RECEIPTS:
            merchant = Merchant(name=r["merchant_name"], address=r["merchant_address"])
            db.add(merchant)
            db.flush()

            receipt = Receipt(
                merchant_id=merchant.id,
                merchant_name=r["merchant_name"],
                merchant_address=r["merchant_address"],
                currency="USD",
                subtotal=r["subtotal"],
                tax=r["tax"],
                total=r["total"],
                payment_method=r["payment_method"],
                purchase_datetime=r["purchase_datetime"],
                image_path="data/uploads/sample-placeholder.png",
                image_hash=f"sample-{r['merchant_name']}-{r['purchase_datetime'].isoformat()}",
                confidence=0.95,
                status="processed",
            )
            for name, qty, price, category in r["items"]:
                receipt.line_items.append(
                    LineItem(
                        name=name, quantity=qty, unit_price=price, total_price=price * qty, category=category
                    )
                )
            db.add(receipt)

        db.commit()
        print(f"Seeded {len(SAMPLE_RECEIPTS)} sample receipts.")
        print("Run POST /reindex (with a real GEMINI_API_KEY) to enable semantic search over them.")


if __name__ == "__main__":
    seed()
