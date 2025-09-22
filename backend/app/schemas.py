from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ORMModel(BaseModel):
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class ProviderSummary(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    website: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class BrandSummary(ORMModel):
    id: uuid.UUID
    name: str
    slug: str


class CategorySummary(ORMModel):
    id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None = None


class ProviderOffer(ORMModel):
    id: uuid.UUID
    provider: ProviderSummary
    unit_of_measure: str | None = None
    currency: str
    list_price: float | None = Field(None, alias="list_price")
    price: float | None
    inventory_quantity: float | None = None
    inventory_updated_at: datetime | None = None


class ProductSummary(ORMModel):
    id: uuid.UUID
    sku: str
    name: str
    description: str | None = None
    brand: BrandSummary | None = None
    default_category: CategorySummary | None = None
    lowest_price: float | None = None
    highest_price: float | None = None
    provider_count: int = 0


class ProductDetail(ProductSummary):
    attributes: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    offers: list[ProviderOffer] = []


class FacetCount(BaseModel):
    key: str
    value: str
    label: str
    count: int


class SearchResponse(BaseModel):
    results: list[ProductSummary]
    total: int
    facets: dict[str, list[FacetCount]]


class ProviderOffering(BaseModel):
    provider: ProviderSummary
    product: ProductSummary
    offer: ProviderOffer


class ProviderOfferingsResponse(BaseModel):
    provider: ProviderSummary
    total: int
    page: int
    page_size: int
    items: list[ProviderOffering]


class CompareResponse(BaseModel):
    sku: str
    offers: list[ProviderOffer]
