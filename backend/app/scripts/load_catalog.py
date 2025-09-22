from __future__ import annotations

import argparse
import asyncio
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

from ..database import SessionLocal
from ..models import Category, Product, Provider, ProviderProduct


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def parse_decimal(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    cleaned = str(value).replace("$", "").replace(",", "").strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


async def load_dataframe(path: Path, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name)
    df = df.rename(
        columns={
            "Vendor": "vendor",
            "Description": "description",
            "Manufacturer Part Number": "sku",
            "List Price": "list_price",
            "NASPO Price": "contract_price",
        }
    )
    expected_columns = {"vendor", "description", "sku", "list_price", "contract_price"}
    missing = expected_columns - set(df.columns)
    if missing:
        raise ValueError(f"Spreadsheet missing columns: {', '.join(sorted(missing))}")

    df = df.dropna(subset=["sku", "vendor"]).copy()
    df["sku"] = df["sku"].astype(str).str.strip()
    df["vendor"] = df["vendor"].astype(str).str.strip()
    df["description"] = df["description"].fillna("").astype(str).str.strip()
    df = df[df["sku"] != ""]
    df = df.drop_duplicates(subset=["vendor", "sku"])

    df["list_price"] = df["list_price"].apply(parse_decimal)
    df["contract_price"] = df["contract_price"].apply(parse_decimal)

    df["category"] = "Uncategorized"
    df["brand"] = "Unspecified"

    return df


async def ensure_default_category(session) -> Category:
    result = await session.execute(select(Category).where(Category.slug == "uncategorized"))
    category = result.scalar_one_or_none()
    if category:
        return category
    category = Category(name="Uncategorized", slug="uncategorized")
    session.add(category)
    await session.flush()
    return category


async def process_row(
    session,
    caches,
    row: dict[str, Any],
    default_category: Category,
):
    vendor_name = row["vendor"].strip()
    sku = row["sku"].strip()
    description = row.get("description") or sku

    provider = caches["providers"].get(vendor_name.lower())
    if not provider:
        result = await session.execute(select(Provider).where(Provider.name == vendor_name))
        provider = result.scalar_one_or_none()
        if not provider:
            slug_base = slugify(vendor_name)
            slug = slug_base
            counter = 1
            while True:
                slug_check = await session.execute(select(Provider).where(Provider.slug == slug))
                if slug_check.scalar_one_or_none() is None:
                    break
                counter += 1
                slug = f"{slug_base}-{counter}"
            provider = Provider(name=vendor_name, slug=slug)
            session.add(provider)
            await session.flush()
        caches["providers"][vendor_name.lower()] = provider

    product = caches["products"].get(sku)
    if not product:
        result = await session.execute(select(Product).where(Product.sku == sku))
        product = result.scalar_one_or_none()
        if not product:
            product = Product(
                sku=sku,
                name=description[:255] or sku,
                description=description,
                default_category=default_category,
            )
            session.add(product)
            await session.flush()
        caches["products"][sku] = product

    stmt = select(ProviderProduct).where(
        ProviderProduct.provider_id == provider.id,
        ProviderProduct.product_id == product.id,
    )
    provider_product = (await session.execute(stmt)).scalar_one_or_none()
    if not provider_product:
        provider_product = ProviderProduct(
            provider=provider,
            product=product,
            list_price=row.get("list_price"),
            price=row.get("contract_price"),
            unit_of_measure="each",
        )
        session.add(provider_product)
    else:
        provider_product.list_price = row.get("list_price")
        provider_product.price = row.get("contract_price")


async def summarize(df: pd.DataFrame):
    provider_counts = df.groupby("vendor")["sku"].nunique().sort_values(ascending=False)
    print("Loaded providers:")
    for vendor, count in provider_counts.items():
        print(f"  - {vendor}: {count} products")

    category_counts = df.groupby("category")["sku"].nunique().sort_values(ascending=False)
    brand_counts = df.groupby("brand")["sku"].nunique().sort_values(ascending=False)

    print("\nCategory coverage:")
    for category, count in category_counts.items():
        print(f"  - {category}: {count} products")

    print("\nBrand coverage:")
    for brand, count in brand_counts.items():
        print(f"  - {brand}: {count} products")

    print("\nDataset totals:")
    print(f"  Providers: {provider_counts.shape[0]}")
    print(f"  Categories: {category_counts.shape[0]}")
    print(f"  Brands: {brand_counts.shape[0]}")
    print(f"  Products: {df['sku'].nunique()}")


async def main(path: Path, sheet_name: str):
    df = await load_dataframe(path, sheet_name)
    await summarize(df)

    async with SessionLocal() as session:
        default_category = await ensure_default_category(session)
        caches: dict[str, dict[str, Any]] = {"providers": {}, "products": {}}

        for record in df.to_dict(orient="records"):
            await process_row(session, caches, record, default_category)

        await session.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load NASPO-style Excel catalog into the database")
    parser.add_argument("excel_path", type=Path, help="Path to the Excel workbook")
    parser.add_argument(
        "--sheet",
        default="NASPO August 2025",
        help="Worksheet name to import",
    )
    args = parser.parse_args()

    asyncio.run(main(args.excel_path, args.sheet))
