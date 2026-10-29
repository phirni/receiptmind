"""SQLAlchemy engine and session management."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def _make_engine() -> Engine:
    is_sqlite = settings.database_url.startswith("sqlite:")
    connect_args: dict[str, object] = {"check_same_thread": False} if is_sqlite else {}
    database_url = settings.database_url
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if not is_sqlite:
        # Supabase's transaction pooler may route consecutive statements to
        # different server connections, so do not use psycopg prepared plans.
        connect_args["prepare_threshold"] = None
    if is_sqlite:
        Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True, future=True)

    if is_sqlite:
        import sqlite_vec

        @event.listens_for(engine, "connect")
        def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
            # Load sqlite-vec only for SQLite connections.
            dbapi_connection.enable_load_extension(True)
            sqlite_vec.load(dbapi_connection)
            dbapi_connection.enable_load_extension(False)

            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

    return engine


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator:
    """FastAPI dependency yielding a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
