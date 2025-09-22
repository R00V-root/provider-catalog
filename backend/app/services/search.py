from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ..models import Brand, Category, Product, Provider, ProviderProduct
from ..schemas import FacetCount, ProductDetail, ProductSummary, ProviderOffer, ProviderOffering, SearchResponse


@dataclass
class SearchFilters:
    providers: set[str]
    brands: set[str]
    categories: set[str]

    @classmethod
    def parse(cls, raw: str | None) -> "SearchFilters":
        providers: set[str] = set()
        brands: set[str] = set()
        categories: set[str] = set()

        if raw:
            for chunk in raw.split(";"):
                if not chunk or ":" not in chunk:
                    continue
                key, values = chunk.split(":", 1)
                ids = {value.strip() for value in values.split(",") if value.strip()}
                if key == "provider":
                    providers.update(ids)
                elif key == "brand":
                    brands.update(ids)
                elif key == "category":
                    categories.update(ids)

        return cls(providers=providers, brands=brands, categories=categories)


def build_conditions(filters: SearchFilters, query: str | None):
    conditions = []
    if filters.providers:
        conditions.append(Provider.id.in_(filters.providers))
    if filters.brands:
        conditions.append(Product.brand_id.in_(filters.brands))
    if filters.categories:
        conditions.append(Product.default_category_id.in_(filters.categories))

    if query:
        document = func.concat_ws(
            " ",
            Product.sku,
            Product.name,
            func.coalesce(Product.description, ""),
        )
        ts_vector = func.to_tsvector("simple", document)
        ts_query = func.plainto_tsquery("simple", query)
        conditions.append(ts_vector.op("@@")(ts_query))

    return conditions


async def search_products(
    session: AsyncSession,
    query: str | None,
    filters: SearchFilters,
    page: int,
    page_size: int,
    sort: str,
) -> SearchResponse:
    conditions = build_conditions(filters, query)
    DefaultCategory = aliased(Category)

    min_price = func.min(func.coalesce(ProviderProduct.price, ProviderProduct.list_price)).label(
        "lowest_price"
    )
    max_price = func.max(func.coalesce(ProviderProduct.price, ProviderProduct.list_price)).label(
        "highest_price"
    )
    provider_count = func.count(distinct(ProviderProduct.provider_id)).label("provider_count")

    stmt = (
        select(
            Product,
            Brand,
            DefaultCategory,
            provider_count,
            min_price,
            max_price,
        )
        .select_from(Product)
        .outerjoin(Brand, Brand.id == Product.brand_id)
        .outerjoin(DefaultCategory, DefaultCategory.id == Product.default_category_id)
        .outerjoin(ProviderProduct, ProviderProduct.product_id == Product.id)
        .outerjoin(Provider, Provider.id == ProviderProduct.provider_id)
        .where(*conditions)
        .group_by(Product.id, Brand.id, DefaultCategory.id)
    )

    if query:
        document = func.concat_ws(
            " ",
            Product.sku,
            Product.name,
            func.coalesce(Product.description, ""),
        )
        ts_query = func.plainto_tsquery("simple", query)
        rank = func.ts_rank_cd(func.to_tsvector("simple", document), ts_query)
    else:
        rank = None

    if sort == "price":
        stmt = stmt.order_by(min_price.asc().nullslast(), Product.name.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(min_price.desc().nullslast(), Product.name.asc())
    elif sort == "name_desc":
        stmt = stmt.order_by(Product.name.desc())
    else:
        orderings = []
        if rank is not None:
            orderings.append(rank.desc())
        orderings.append(Product.name.asc())
        stmt = stmt.order_by(*orderings)

    stmt = stmt.offset(page * page_size).limit(page_size)

    result = await session.execute(stmt)
    rows = result.all()

    products: list[ProductSummary] = []
    for product, brand, category, provider_count_value, min_price_value, max_price_value in rows:
        products.append(
            ProductSummary(
                id=product.id,
                sku=product.sku,
                name=product.name,
                description=product.description,
                brand=brand,
                default_category=category,
                lowest_price=float(min_price_value) if min_price_value is not None else None,
                highest_price=float(max_price_value) if max_price_value is not None else None,
                provider_count=provider_count_value or 0,
            )
        )

    # Total count
    count_stmt = (
        select(func.count(distinct(Product.id)))
        .select_from(Product)
        .outerjoin(Brand, Brand.id == Product.brand_id)
        .outerjoin(DefaultCategory, DefaultCategory.id == Product.default_category_id)
        .outerjoin(ProviderProduct, ProviderProduct.product_id == Product.id)
        .outerjoin(Provider, Provider.id == ProviderProduct.provider_id)
        .where(*conditions)
    )
    total = (await session.execute(count_stmt)).scalar_one()

    facets = await build_facets(session, conditions)

    return SearchResponse(results=products, total=total, facets=facets)


async def build_facets(
    session: AsyncSession,
    conditions: Iterable,
) -> dict[str, list[FacetCount]]:
    facets: dict[str, list[FacetCount]] = {"provider": [], "brand": [], "category": []}
    DefaultCategory = aliased(Category)

    provider_stmt = (
        select(
            Provider.id,
            Provider.name,
            func.count(distinct(Product.id)).label("count"),
        )
        .select_from(Product)
        .outerjoin(ProviderProduct, ProviderProduct.product_id == Product.id)
        .outerjoin(Provider, Provider.id == ProviderProduct.provider_id)
        .where(*conditions)
        .group_by(Provider.id, Provider.name)
        .order_by(Provider.name.asc())
    )
    provider_rows = (await session.execute(provider_stmt)).all()
    facets["provider"] = [
        FacetCount(key="provider", value=str(provider_id), label=name, count=count or 0)
        for provider_id, name, count in provider_rows
        if provider_id is not None
    ]

    brand_stmt = (
        select(
            Brand.id,
            Brand.name,
            func.count(distinct(Product.id)).label("count"),
        )
        .select_from(Product)
        .outerjoin(Brand, Brand.id == Product.brand_id)
        .outerjoin(ProviderProduct, ProviderProduct.product_id == Product.id)
        .outerjoin(Provider, Provider.id == ProviderProduct.provider_id)
        .where(*conditions)
        .group_by(Brand.id, Brand.name)
        .order_by(Brand.name.asc())
    )
    brand_rows = (await session.execute(brand_stmt)).all()
    facets["brand"] = [
        FacetCount(key="brand", value=str(brand_id), label=name, count=count or 0)
        for brand_id, name, count in brand_rows
        if brand_id is not None
    ]

    category_stmt = (
        select(
            DefaultCategory.id,
            DefaultCategory.name,
            func.count(distinct(Product.id)).label("count"),
        )
        .select_from(Product)
        .outerjoin(DefaultCategory, DefaultCategory.id == Product.default_category_id)
        .outerjoin(ProviderProduct, ProviderProduct.product_id == Product.id)
        .outerjoin(Provider, Provider.id == ProviderProduct.provider_id)
        .where(*conditions)
        .group_by(DefaultCategory.id, DefaultCategory.name)
        .order_by(DefaultCategory.name.asc())
    )
    category_rows = (await session.execute(category_stmt)).all()
    facets["category"] = [
        FacetCount(key="category", value=str(category_id), label=name, count=count or 0)
        for category_id, name, count in category_rows
        if category_id is not None
    ]

    return facets


async def load_product_detail(session: AsyncSession, product_id: str) -> ProductDetail | None:
    product = await session.get(Product, product_id)
    if not product:
        return None

    await session.refresh(
        product,
        attribute_names=["provider_offers", "attributes", "images", "brand", "default_category"],
    )

    offers = []
    for offer in product.provider_offers:
        await session.refresh(offer, attribute_names=["provider"])
        offers.append(
            ProviderOffer(
                id=offer.id,
                provider=offer.provider,
                unit_of_measure=offer.unit_of_measure,
                currency=offer.currency,
                list_price=float(offer.list_price) if offer.list_price is not None else None,
                price=float(offer.price) if offer.price is not None else None,
                inventory_quantity=offer.inventory_quantity,
                inventory_updated_at=offer.inventory_updated_at,
            )
        )

    attributes = [
        {"key": attribute.key, "value": attribute.value, "value_type": attribute.value_type}
        for attribute in product.attributes
    ]
    images = [
        {"url": image.url, "alt_text": image.alt_text, "sort_order": image.sort_order}
        for image in sorted(product.images, key=lambda img: img.sort_order)
    ]

    prices = [offer.price or offer.list_price for offer in offers if (offer.price or offer.list_price) is not None]

    return ProductDetail(
        id=product.id,
        sku=product.sku,
        name=product.name,
        description=product.description,
        brand=product.brand,
        default_category=product.default_category,
        lowest_price=float(min(prices)) if prices else None,
        highest_price=float(max(prices)) if prices else None,
        provider_count=len(offers),
        attributes=attributes,
        images=images,
        offers=offers,
    )


async def load_provider_offerings(
    session: AsyncSession, provider_id: str, page: int, page_size: int
) -> tuple[list[ProviderOffering], int]:
    stmt = (
        select(ProviderProduct)
        .where(ProviderProduct.provider_id == provider_id)
        .order_by(ProviderProduct.created_at.desc())
        .offset(page * page_size)
        .limit(page_size)
    )
    offers_result = await session.execute(stmt)
    offerings = []
    for offer in offers_result.scalars():
        await session.refresh(offer, attribute_names=["product", "provider"])
        provider_data = offer.provider
        product_data = offer.product
        await session.refresh(product_data, attribute_names=["brand", "default_category"])
        product_summary = ProductSummary(
            id=product_data.id,
            sku=product_data.sku,
            name=product_data.name,
            description=product_data.description,
            brand=product_data.brand,
            default_category=product_data.default_category,
            lowest_price=float(offer.price or offer.list_price) if (offer.price or offer.list_price) is not None else None,
            highest_price=float(offer.price or offer.list_price) if (offer.price or offer.list_price) is not None else None,
            provider_count=1,
        )
        provider_offer = ProviderOffer(
            id=offer.id,
            provider=provider_data,
            unit_of_measure=offer.unit_of_measure,
            currency=offer.currency,
            list_price=float(offer.list_price) if offer.list_price is not None else None,
            price=float(offer.price) if offer.price is not None else None,
            inventory_quantity=offer.inventory_quantity,
            inventory_updated_at=offer.inventory_updated_at,
        )
        offerings.append(
            ProviderOffering(
                provider=provider_data,
                product=product_summary,
                offer=provider_offer,
            )
        )

    total_stmt = select(func.count()).select_from(ProviderProduct).where(ProviderProduct.provider_id == provider_id)
    total = (await session.execute(total_stmt)).scalar_one()
    return offerings, total


async def compare_offers(session: AsyncSession, sku: str) -> list[ProviderOffer]:
    product_stmt = select(Product.id).where(Product.sku == sku)
    product_id = (await session.execute(product_stmt)).scalar_one_or_none()
    if not product_id:
        return []

    offers_stmt = (
        select(ProviderProduct)
        .where(ProviderProduct.product_id == product_id)
        .order_by(func.coalesce(ProviderProduct.price, ProviderProduct.list_price).asc())
    )
    offers_result = await session.execute(offers_stmt)

    offers: list[ProviderOffer] = []
    for offer in offers_result.scalars():
        await session.refresh(offer, attribute_names=["provider"])
        offers.append(
            ProviderOffer(
                id=offer.id,
                provider=offer.provider,
                unit_of_measure=offer.unit_of_measure,
                currency=offer.currency,
                list_price=float(offer.list_price) if offer.list_price is not None else None,
                price=float(offer.price) if offer.price is not None else None,
                inventory_quantity=offer.inventory_quantity,
                inventory_updated_at=offer.inventory_updated_at,
            )
        )

    return offers
