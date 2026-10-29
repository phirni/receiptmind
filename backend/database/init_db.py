"""Create relational tables and the configured vector store on startup."""

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
    if engine.dialect.name == "postgresql":
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS extensions")
            connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        init_vector_store(db, settings.embedding_dimensions)
    logger.info("Database initialized using %s", engine.dialect.name)
