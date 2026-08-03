"""POST /search and POST /reindex."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.deps import get_embedding_service, get_search_service
from backend.schemas.api import SearchQuery, SearchResponse
from backend.services.embedding_service import EmbeddingService
from backend.services.search_service import SearchService

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search_receipts(
    query: SearchQuery, service: SearchService = Depends(get_search_service)
) -> SearchResponse:
    results = await service.search(query)
    return SearchResponse(query=query.query, mode=query.mode, results=results, count=len(results))


@router.post("/reindex")
async def reindex(service: EmbeddingService = Depends(get_embedding_service)) -> dict:
    count = await service.reindex_all()
    return {"reindexed_items": count}
