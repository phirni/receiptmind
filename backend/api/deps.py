"""Dependency-injection wiring for FastAPI routes.

Every route depends on these functions rather than constructing services or
providers itself, so tests can override any of them independently.
"""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.database.session import get_db
from backend.embeddings.base import EmbeddingProvider
from backend.embeddings.factory import get_embedding_provider
from backend.providers.base import VisionProvider
from backend.providers.factory import get_vision_provider
from backend.services.embedding_service import EmbeddingService
from backend.services.extraction_service import ExtractionService
from backend.services.receipt_service import ReceiptService
from backend.services.search_service import SearchService
from backend.services.stats_service import StatsService


def get_app_settings() -> Settings:
    return get_settings()


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_vision_provider_dep(settings: Settings = Depends(get_app_settings)) -> VisionProvider:
    return get_vision_provider(settings)


def get_embedding_provider_dep(settings: Settings = Depends(get_app_settings)) -> EmbeddingProvider:
    return get_embedding_provider(settings)


def get_extraction_service(
    db: Session = Depends(get_db_session),
    provider: VisionProvider = Depends(get_vision_provider_dep),
    settings: Settings = Depends(get_app_settings),
) -> ExtractionService:
    return ExtractionService(db, provider, settings)


def get_embedding_service(
    db: Session = Depends(get_db_session),
    provider: EmbeddingProvider = Depends(get_embedding_provider_dep),
) -> EmbeddingService:
    return EmbeddingService(db, provider)


def get_receipt_service(db: Session = Depends(get_db_session)) -> ReceiptService:
    return ReceiptService(db)


def get_search_service(
    db: Session = Depends(get_db_session),
    provider: EmbeddingProvider = Depends(get_embedding_provider_dep),
) -> SearchService:
    return SearchService(db, provider)


def get_stats_service(db: Session = Depends(get_db_session)) -> StatsService:
    return StatsService(db)
