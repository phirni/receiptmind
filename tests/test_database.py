"""Tests for ORM models and the sqlite-vec vector store wrapper."""

from __future__ import annotations

from backend.models.receipt import LineItem, Merchant, Receipt
from backend.search.vector_store import delete_embedding, knn_search, upsert_embedding
from tests.conftest import TEST_EMBEDDING_DIM


def _make_receipt(db, merchant_name="Test Store", n_items=2):
    merchant = Merchant(name=merchant_name)
    db.add(merchant)
    db.flush()
    receipt = Receipt(
        merchant_id=merchant.id,
        merchant_name=merchant_name,
        total=10.0,
        image_path="/tmp/fake.png",
        image_hash=f"hash-{merchant_name}-{n_items}",
        status="processed",
    )
    for i in range(n_items):
        receipt.line_items.append(LineItem(name=f"Item {i}", quantity=1, total_price=5.0))
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def test_receipt_and_line_items_persist(db_session_factory):
    with db_session_factory() as db:
        receipt = _make_receipt(db)
        assert receipt.id is not None
        assert len(receipt.line_items) == 2


def test_cascade_delete_removes_line_items(db_session_factory):
    with db_session_factory() as db:
        receipt = _make_receipt(db)
        receipt_id = receipt.id
        db.delete(receipt)
        db.commit()

        remaining = db.query(LineItem).filter(LineItem.receipt_id == receipt_id).count()
        assert remaining == 0


def test_merchant_unique_constraint_allows_same_name_different_address(db_session_factory):
    with db_session_factory() as db:
        m1 = Merchant(name="Cafe X", address="123 Main St")
        m2 = Merchant(name="Cafe X", address="456 Oak Ave")
        db.add_all([m1, m2])
        db.commit()
        assert m1.id != m2.id


def test_vector_store_upsert_and_knn_search(db_session_factory):
    with db_session_factory() as db:
        receipt = _make_receipt(db, n_items=1)
        item = receipt.line_items[0]

        vector = [1.0] + [0.0] * (TEST_EMBEDDING_DIM - 1)
        upsert_embedding(db, item.id, vector)
        db.commit()

        results = knn_search(db, vector, k=5)
        assert results
        assert results[0][0] == item.id
        assert results[0][1] < 1e-6  # identical vector -> ~0 distance


def test_vector_store_delete_embedding(db_session_factory):
    with db_session_factory() as db:
        receipt = _make_receipt(db, n_items=1)
        item = receipt.line_items[0]
        vector = [1.0] + [0.0] * (TEST_EMBEDDING_DIM - 1)
        upsert_embedding(db, item.id, vector)
        db.commit()

        delete_embedding(db, item.id)
        db.commit()

        results = knn_search(db, vector, k=5)
        assert all(r[0] != item.id for r in results)


def test_vector_store_upsert_overwrites_previous_embedding(db_session_factory):
    with db_session_factory() as db:
        receipt = _make_receipt(db, n_items=1)
        item = receipt.line_items[0]

        upsert_embedding(db, item.id, [1.0] + [0.0] * (TEST_EMBEDDING_DIM - 1))
        db.commit()
        upsert_embedding(db, item.id, [0.0, 1.0] + [0.0] * (TEST_EMBEDDING_DIM - 2))
        db.commit()

        query = [0.0, 1.0] + [0.0] * (TEST_EMBEDDING_DIM - 2)
        results = knn_search(db, query, k=5)
        assert results[0][0] == item.id
        assert results[0][1] < 1e-6
