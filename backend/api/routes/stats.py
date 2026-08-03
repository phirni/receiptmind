"""GET /stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import get_stats_service
from backend.schemas.api import StatsResponse
from backend.services.stats_service import StatsService

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
def get_stats(service: StatsService = Depends(get_stats_service)) -> StatsResponse:
    return service.get_stats()
