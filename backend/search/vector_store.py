"""Vector storage adapters for local sqlite-vec and production pgvector.

sqlite-vec's `vec0` virtual tables key rows by an INTEGER rowid, but our
domain ids are UUID hex strings (see models.receipt). `vec_id_map` bridges
the two: it owns the autoincrement integer rowid and maps it 1:1 to a
`line_item_id`.
"""

from __future__ import annotations

import struct

from sqlalchemy import text
from sqlalchemy.orm import Session

_CREATE_MAP_TABLE = """
CREATE TABLE IF NOT EXISTS vec_id_map (
    vec_rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    line_item_id TEXT NOT NULL UNIQUE
)
"""


def _create_vec_table_sql(dimensions: int) -> str:
    return (
        f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_line_items "
        f"USING vec0(embedding float[{dimensions}] distance_metric=cosine)"
    )


def _serialize(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


def init_vector_store(db: Session, dimensions: int) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions"))
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS line_item_embeddings ("
                "line_item_id VARCHAR(32) PRIMARY KEY REFERENCES line_items(id) ON DELETE CASCADE, "
                f"embedding extensions.vector({int(dimensions)}) NOT NULL)"
            )
        )
        db.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_line_item_embeddings_hnsw "
                "ON line_item_embeddings USING hnsw (embedding extensions.vector_cosine_ops)"
            )
        )
    else:
        db.execute(text(_CREATE_MAP_TABLE))
        db.execute(text(_create_vec_table_sql(dimensions)))
    db.commit()


def upsert_embedding(db: Session, line_item_id: str, embedding: list[float]) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        vector_value = "[" + ",".join(str(value) for value in embedding) + "]"
        db.execute(
            text(
                "INSERT INTO line_item_embeddings (line_item_id, embedding) "
                "VALUES (:id, CAST(:embedding AS extensions.vector)) "
                "ON CONFLICT (line_item_id) DO UPDATE SET embedding = EXCLUDED.embedding"
            ),
            {"id": line_item_id, "embedding": vector_value},
        )
        return

    db.execute(
        text("INSERT INTO vec_id_map (line_item_id) VALUES (:id) ON CONFLICT(line_item_id) DO NOTHING"),
        {"id": line_item_id},
    )
    rowid = db.execute(
        text("SELECT vec_rowid FROM vec_id_map WHERE line_item_id = :id"), {"id": line_item_id}
    ).scalar_one()
    db.execute(text("DELETE FROM vec_line_items WHERE rowid = :rowid"), {"rowid": rowid})
    db.execute(
        text("INSERT INTO vec_line_items (rowid, embedding) VALUES (:rowid, :embedding)"),
        {"rowid": rowid, "embedding": _serialize(embedding)},
    )


def delete_embedding(db: Session, line_item_id: str) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("DELETE FROM line_item_embeddings WHERE line_item_id = :id"), {"id": line_item_id})
        return

    row = db.execute(
        text("SELECT vec_rowid FROM vec_id_map WHERE line_item_id = :id"), {"id": line_item_id}
    ).first()
    if row is None:
        return
    db.execute(text("DELETE FROM vec_line_items WHERE rowid = :rowid"), {"rowid": row.vec_rowid})
    db.execute(text("DELETE FROM vec_id_map WHERE vec_rowid = :rowid"), {"rowid": row.vec_rowid})


def knn_search(db: Session, query_embedding: list[float], k: int) -> list[tuple[str, float]]:
    """Return up to `k` (line_item_id, distance) pairs, nearest first."""
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        vector_value = "[" + ",".join(str(value) for value in query_embedding) + "]"
        rows = db.execute(
            text(
                "SELECT line_item_id, embedding <=> CAST(:embedding AS extensions.vector) AS distance "
                "FROM line_item_embeddings ORDER BY embedding <=> CAST(:embedding AS extensions.vector) "
                "LIMIT :k"
            ),
            {"embedding": vector_value, "k": k},
        ).all()
        return [(row.line_item_id, row.distance) for row in rows]

    rows = db.execute(
        text("""
            SELECT m.line_item_id AS line_item_id, v.distance AS distance
            FROM vec_line_items v
            JOIN vec_id_map m ON m.vec_rowid = v.rowid
            WHERE v.embedding MATCH :embedding AND k = :k
            ORDER BY v.distance
            """),
        {"embedding": _serialize(query_embedding), "k": k},
    ).all()
    return [(r.line_item_id, r.distance) for r in rows]
