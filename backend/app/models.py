from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    website: Mapped[str | None] = mapped_column(String(255))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text())
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), server_onupdate=func.now()
    )

    products: Mapped[list["ProviderProduct"]] = relationship(back_populates="provider")


class Brand(Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    products: Mapped[list["Product"]] = relationship(back_populates="brand")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))

    parent: Mapped[Category | None] = relationship(remote_side="Category.id")
    products: Mapped[list["ProductCategory"]] = relationship(back_populates="category")

    __table_args__ = (UniqueConstraint("name", "parent_id", name="uq_categories_name_parent"),)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    brand_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("brands.id"))
    default_category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), server_onupdate=func.now()
    )

    brand: Mapped[Brand | None] = relationship(back_populates="products")
    default_category: Mapped[Category | None] = relationship()
    categories: Mapped[list["ProductCategory"]] = relationship(back_populates="product")
    provider_offers: Mapped[list["ProviderProduct"]] = relationship(back_populates="product")
    attributes: Mapped[list["ProductAttribute"]] = relationship(back_populates="product")
    images: Mapped[list["ProductImage"]] = relationship(back_populates="product")


class ProductCategory(Base):
    __tablename__ = "product_categories"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )

    product: Mapped[Product] = relationship(back_populates="categories")
    category: Mapped[Category] = relationship(back_populates="products")


class ProviderProduct(Base):
    __tablename__ = "provider_products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    unit_of_measure: Mapped[str | None] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    list_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    inventory_quantity: Mapped[float | None] = mapped_column(Float)
    inventory_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), server_onupdate=func.now()
    )

    provider: Mapped[Provider] = relationship(back_populates="products")
    product: Mapped[Product] = relationship(back_populates="provider_offers")
    attributes: Mapped[list["ProviderProductAttribute"]] = relationship(back_populates="provider_product")

    __table_args__ = (
        UniqueConstraint("provider_id", "product_id", name="uq_provider_product"),
    )


class ProductAttribute(Base):
    __tablename__ = "product_attributes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text(), nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")

    product: Mapped[Product] = relationship(back_populates="attributes")

    __table_args__ = (UniqueConstraint("product_id", "key", name="uq_product_attribute"),)


class ProviderProductAttribute(Base):
    __tablename__ = "provider_product_attributes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider_product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("provider_products.id", ondelete="CASCADE")
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text(), nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")

    provider_product: Mapped[ProviderProduct] = relationship(back_populates="attributes")

    __table_args__ = (
        UniqueConstraint("provider_product_id", "key", name="uq_provider_product_attribute"),
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    product: Mapped[Product] = relationship(back_populates="images")


Index(
    "ix_products_search_vector",
    text("to_tsvector('simple', coalesce(sku,'') || ' ' || coalesce(name,'') || ' ' || coalesce(description,''))"),
    postgresql_using="gin",
)

Index(
    "ix_products_name_trgm",
    Product.name,
    postgresql_using="gin",
    postgresql_ops={"name": "gin_trgm_ops"},
)

Index(
    "ix_products_sku_trgm",
    Product.sku,
    postgresql_using="gin",
    postgresql_ops={"sku": "gin_trgm_ops"},
)
