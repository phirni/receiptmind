"""POST /upload — accepts one or many receipt images/PDFs."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.orm import Session

from backend.api.deps import (
    get_app_settings,
    get_db_session,
    get_embedding_provider_dep,
    get_extraction_service,
)
from backend.config import Settings
from backend.embeddings.base import EmbeddingProvider
from backend.models.receipt import Receipt
from backend.schemas.api import UploadResponse, UploadResultItem
from backend.services.embedding_service import EmbeddingService
from backend.services.extraction_service import ExtractionService
from backend.utils.exceptions import ReceiptMindError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["upload"])


async def _embed_receipt_task(receipt_id: str, provider: EmbeddingProvider) -> None:
    """Background task: re-open a fresh DB session so it survives past the request."""
    from backend.database.session import SessionLocal
    from backend.services.receipt_service import ReceiptService

    with SessionLocal() as db:
        try:
            receipt = ReceiptService(db).get(receipt_id)
            await EmbeddingService(db, provider).embed_receipt(receipt)
        except Exception:  # noqa: BLE001
            logger.exception("Background embedding failed for receipt %s", receipt_id)


@router.post("/upload", response_model=UploadResponse)
async def upload_receipts(
    background_tasks: BackgroundTasks,
    files: list[UploadFile],
    extraction_service: ExtractionService = Depends(get_extraction_service),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider_dep),
    settings: Settings = Depends(get_app_settings),
    db: Session = Depends(get_db_session),
) -> UploadResponse:
    results: list[UploadResultItem] = []
    accepted = 0
    rejected = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024

    for upload in files:
        raw = await upload.read()
        if len(raw) > max_bytes:
            rejected += 1
            results.append(
                UploadResultItem(
                    filename=upload.filename or "unknown",
                    status="rejected",
                    detail=f"File exceeds {settings.max_upload_mb}MB limit.",
                )
            )
            continue

        try:
            receipt: Receipt = await extraction_service.process_upload(
                raw, upload.content_type or "", upload.filename or "upload"
            )
        except ReceiptMindError as exc:
            rejected += 1
            results.append(
                UploadResultItem(filename=upload.filename or "unknown", status="rejected", detail=exc.message)
            )
            continue

        if receipt.status == "failed":
            rejected += 1
            results.append(
                UploadResultItem(
                    filename=upload.filename or "unknown",
                    status="rejected",
                    receipt_id=receipt.id,
                    detail=receipt.error_message,
                )
            )
            continue

        accepted += 1
        results.append(
            UploadResultItem(filename=upload.filename or "unknown", status="queued", receipt_id=receipt.id)
        )
        background_tasks.add_task(_embed_receipt_task, receipt.id, embedding_provider)

    return UploadResponse(accepted=accepted, rejected=rejected, results=results)
