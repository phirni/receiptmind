"""GET /receipts, GET /receipts/{id}, DELETE /receipts/{id}."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query, status

from backend.api.deps import get_receipt_service
from backend.schemas.api import PaginatedReceipts, ReceiptRead
from backend.services.receipt_service import ReceiptService

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("", response_model=PaginatedReceipts)
def list_receipts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    merchant: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    service: ReceiptService = Depends(get_receipt_service),
) -> PaginatedReceipts:
    return service.list(
        page=page,
        page_size=page_size,
        merchant=merchant,
        date_from=date_from,
        date_to=date_to,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get("/{receipt_id}", response_model=ReceiptRead)
def get_receipt(receipt_id: str, service: ReceiptService = Depends(get_receipt_service)) -> ReceiptRead:
    return service.get(receipt_id)  # type: ignore[return-value]


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(receipt_id: str, service: ReceiptService = Depends(get_receipt_service)) -> None:
    service.delete(receipt_id)
