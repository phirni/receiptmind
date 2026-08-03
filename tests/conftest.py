"""Shared pytest fixtures.

Every test gets a fresh, isolated sqlite file (not `:memory:`, because
sqlite-vec's virtual tables and our multi-connection FastAPI app work more
predictably against a real file) and a FastAPI TestClient wired to it via
dependency overrides — no real network calls are made in the test suite.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import sqlite_vec
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.api.deps import (
    get_db_session,
    get_embedding_provider_dep,
    get_vision_provider_dep,
)
from backend.database.session import Base
from backend.embeddings.base import EmbeddingProvider
from backend.main import app
from backend.models import receipt  # noqa: F401
from backend.providers.base import VisionProvider
from backend.schemas.extraction import ExtractedLineItem, ExtractedReceipt
from backend.search.vector_store import init_vector_store

TEST_EMBEDDING_DIM = 8


@pytest.fixture
def db_session_factory():
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _configure(dbapi_connection, _record):
        dbapi_connection.enable_load_extension(True)
        sqlite_vec.load(dbapi_connection)
        dbapi_connection.enable_load_extension(False)
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as db:
        init_vector_store(db, TEST_EMBEDDING_DIM)

    yield SessionLocal
    engine.dispose()


class FakeVisionProvider(VisionProvider):
    """Returns a fixed, valid extraction — no network calls."""

    def __init__(self, response: ExtractedReceipt | None = None, should_fail: bool = False):
        self.response = response or ExtractedReceipt(
            merchant_name="Test Cafe",
            total=10.50,
            subtotal=9.50,
            tax=1.00,
            line_items=[
                ExtractedLineItem(
                    name="Latte", quantity=1, unit_price=5.50, total_price=5.50, category="beverages"
                ),
                ExtractedLineItem(
                    name="Muffin", quantity=1, unit_price=4.00, total_price=4.00, category="snacks"
                ),
            ],
            confidence=0.9,
        )
        self.should_fail = should_fail
        self.call_count = 0

    async def extract_receipt(self, image_bytes: bytes, mime_type: str) -> ExtractedReceipt:
        self.call_count += 1
        if self.should_fail:
            from backend.providers.base import VisionProviderError

            raise VisionProviderError("simulated provider failure")
        return self.response


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic pseudo-embeddings derived from text hashing — no network calls."""

    dimensions = TEST_EMBEDDING_DIM

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        # Deterministic, content-sensitive pseudo-embedding: words sharing
        # tokens end up with non-orthogonal vectors, which is enough to
        # exercise ranking logic in tests without a real model.
        vec = [0.0] * self.dimensions
        for word in text.lower().split():
            h = hash(word)
            vec[h % self.dimensions] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]


@pytest.fixture
def fake_vision_provider():
    return FakeVisionProvider()


@pytest.fixture
def fake_embedding_provider():
    return FakeEmbeddingProvider()


@pytest.fixture
def client(db_session_factory, fake_vision_provider, fake_embedding_provider, tmp_path, monkeypatch):
    from backend.config import get_settings

    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr("backend.main.init_db", lambda: None)

    def _get_db_override():
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db_session] = _get_db_override
    app.dependency_overrides[get_vision_provider_dep] = lambda: fake_vision_provider
    app.dependency_overrides[get_embedding_provider_dep] = lambda: fake_embedding_provider

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
