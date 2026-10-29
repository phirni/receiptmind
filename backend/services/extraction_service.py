"""Turns an uploaded file into a persisted Receipt (+ LineItems).

Pipeline: normalize -> hash/dedup -> vision extraction -> validation
(already enforced by ExtractedReceipt) -> persist -> queue for embedding.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.models.receipt import LineItem, Merchant, Receipt
from backend.providers.base import VisionProvider, VisionProviderError
from backend.schemas.extraction import ExtractedReceipt
from backend.services.image_storage import save_receipt_image
from backend.utils.exceptions import DuplicateReceiptError, ExtractionFailedError
from backend.utils.image_utils import normalize_to_png, sha256_hash

logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(self, db: Session, provider: VisionProvider, settings: Settings) -> None:
        self._db = db
        self._provider = provider
        self._settings = settings

    def check_duplicate(self, image_hash: str) -> Receipt | None:
        return self._db.execute(
            select(Receipt).where(Receipt.image_hash == image_hash, Receipt.status != "failed")
        ).scalar_one_or_none()

    async def process_upload(self, raw_bytes: bytes, content_type: str, filename: str) -> Receipt:
        png_bytes = normalize_to_png(raw_bytes, content_type, filename)
        image_hash = sha256_hash(png_bytes)

        existing = self.check_duplicate(image_hash)
        if existing is not None:
            raise DuplicateReceiptError(f"This receipt was already uploaded (id={existing.id}).")

        image_path = await asyncio.to_thread(save_receipt_image, png_bytes, image_hash, self._settings)

        try:
            extracted = await self._provider.extract_receipt(png_bytes, "image/png")
        except VisionProviderError as exc:
            self._persist_failed(image_path, image_hash, str(exc))
            raise ExtractionFailedError(str(exc)) from exc

        receipt = self._persist_receipt(extracted, image_path, image_hash)
        return receipt

    def _persist_failed(self, image_path: str, image_hash: str, error_message: str) -> Receipt:
        receipt = Receipt(
            merchant_name="Unknown",
            total=0.0,
            image_path=image_path,
            image_hash=image_hash,
            status="failed",
            error_message=error_message,
        )
        self._db.add(receipt)
        self._db.commit()
        self._db.refresh(receipt)
        return receipt

    def _persist_receipt(self, extracted: ExtractedReceipt, image_path: str, image_hash: str) -> Receipt:
        merchant = self._get_or_create_merchant(extracted.merchant_name, extracted.merchant_address)

        receipt = Receipt(
            merchant_id=merchant.id if merchant else None,
            merchant_name=extracted.merchant_name,
            merchant_address=extracted.merchant_address,
            receipt_number=extracted.receipt_number,
            currency=extracted.currency,
            subtotal=extracted.subtotal,
            tax=extracted.tax,
            total=extracted.total,
            payment_method=extracted.payment_method,
            purchase_datetime=extracted.purchase_datetime,
            image_path=image_path,
            image_hash=image_hash,
            raw_extraction=extracted.model_dump_json(),
            confidence=extracted.confidence,
            status="processed",
        )
        for item in extracted.line_items:
            receipt.line_items.append(
                LineItem(
                    name=item.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    category=item.category,
                )
            )

        self._db.add(receipt)
        self._db.commit()
        self._db.refresh(receipt)
        logger.info(
            "Persisted receipt %s (%s, %d items)", receipt.id, receipt.merchant_name, len(receipt.line_items)
        )
        return receipt

    def _get_or_create_merchant(self, name: str, address: str | None) -> Merchant | None:
        if not name:
            return None
        existing = self._db.execute(
            select(Merchant).where(Merchant.name == name, Merchant.address == address)
        ).scalar_one_or_none()
        if existing:
            return existing
        merchant = Merchant(name=name, address=address)
        self._db.add(merchant)
        self._db.flush()
        return merchant
