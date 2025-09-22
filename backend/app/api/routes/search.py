from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...schemas import SearchResponse
from ...services.search import SearchFilters, search_products
from ..deps import get_db_session

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
async def search_catalog(
    q: str | None = Query(None, description="Full text search query"),
    filters: str | None = Query(
        None,
        description="Semicolon delimited filters, e.g. provider:uuid1,uuid2;brand:uuid3",
    ),
    page: int = Query(0, ge=0),
    page_size: int = Query(settings.page_size, ge=1, le=100),
    sort: str = Query("relevance", pattern="^(relevance|price|price_desc|name|name_desc)$"),
    session: AsyncSession = Depends(get_db_session),
) -> SearchResponse:
    parsed_filters = SearchFilters.parse(filters)
    return await search_products(session, q, parsed_filters, page, page_size, sort)
