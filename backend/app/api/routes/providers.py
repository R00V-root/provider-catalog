from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Provider
from ...schemas import ProviderOffering, ProviderOfferingsResponse, ProviderSummary
from ...services.search import load_provider_offerings
from ..deps import get_db_session

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/{provider_id}", response_model=ProviderSummary)
async def get_provider(
    provider_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ProviderSummary:
    provider = await session.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return ProviderSummary.model_validate(provider)


@router.get("/{provider_id}/offerings", response_model=ProviderOfferingsResponse)
async def list_provider_offerings(
    provider_id: str,
    page: int = Query(0, ge=0),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> ProviderOfferingsResponse:
    provider = await session.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    offerings, total = await load_provider_offerings(session, provider_id, page, page_size)
    return ProviderOfferingsResponse(
        provider=ProviderSummary.model_validate(provider),
        total=total,
        page=page,
        page_size=page_size,
        items=offerings,
    )
