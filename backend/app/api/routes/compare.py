from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas import CompareResponse
from ...services.search import compare_offers
from ..deps import get_db_session

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=CompareResponse)
async def compare_by_sku(
    sku: str = Query(..., description="Manufacturer part number / SKU"),
    session: AsyncSession = Depends(get_db_session),
) -> CompareResponse:
    offers = await compare_offers(session, sku)
    if not offers:
        raise HTTPException(status_code=404, detail="No offers found for SKU")
    return CompareResponse(sku=sku, offers=offers)
