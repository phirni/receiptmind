"""Create tables and the sqlite-vec virtual table on startup."""

from __future__ import annotations

import logging

from backend.config import get_settings
from backend.database.session import Base, SessionLocal, engine

# Import models so they register on Base.metadata before create_all runs.
from backend.models import receipt  # noqa: F401
from backend.search.vector_store import init_vector_store

logger = logging.getLogger(__name__)


def init_db() -> None:
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        init_vector_store(db, settings.embedding_dimensions)
    logger.info("Database initialized at %s", settings.sqlite_path)
