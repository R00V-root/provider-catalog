from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas import ProductDetail
from ...services.search import load_product_detail
from ..deps import get_db_session

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(
    product_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> ProductDetail:
    product = await load_product_detail(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product
