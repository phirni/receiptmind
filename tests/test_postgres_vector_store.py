from __future__ import annotations

from types import SimpleNamespace

from backend.search.vector_store import delete_embedding, init_vector_store, knn_search, upsert_embedding


class FakePostgresSession:
    bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))

    def __init__(self):
        self.calls = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        if "SELECT line_item_id" in str(statement):
            return SimpleNamespace(all=lambda: [SimpleNamespace(line_item_id="item-1", distance=0.125)])
        return SimpleNamespace()

    def commit(self):
        self.committed = True


def test_postgres_vector_store_initializes_pgvector_schema():
    db = FakePostgresSession()

    init_vector_store(db, dimensions=768)

    sql = "\n".join(statement for statement, _ in db.calls)
    assert "extensions.vector(768)" in sql
    assert "USING hnsw" in sql
    assert db.committed is True


def test_postgres_embedding_upsert_serializes_vector_for_pgvector():
    db = FakePostgresSession()

    upsert_embedding(db, "item-1", [0.25, -0.5])

    sql, params = db.calls[0]
    assert "ON CONFLICT (line_item_id) DO UPDATE" in sql
    assert params == {"id": "item-1", "embedding": "[0.25,-0.5]"}


def test_postgres_knn_search_and_delete_use_embedding_table():
    db = FakePostgresSession()

    matches = knn_search(db, [0.0, 1.0], k=4)
    delete_embedding(db, "item-1")

    assert matches == [("item-1", 0.125)]
    assert "ORDER BY embedding <=>" in db.calls[0][0]
    assert "DELETE FROM line_item_embeddings" in db.calls[1][0]
