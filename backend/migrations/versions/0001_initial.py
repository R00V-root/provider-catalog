"""initial schema"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')

    op.create_table(
        "providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.UniqueConstraint("name", "parent_id", name="uq_categories_name_parent"),
    )

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("sku", sa.String(length=255), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("brand_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column(
            "default_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "product_categories",
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    op.create_table(
        "provider_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("providers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unit_of_measure", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("list_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("price", sa.Numeric(18, 4), nullable=True),
        sa.Column("inventory_quantity", sa.Float(), nullable=True),
        sa.Column("inventory_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("provider_id", "product_id", name="uq_provider_product"),
    )

    op.create_table(
        "product_attributes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=50), nullable=False, server_default="string"),
        sa.UniqueConstraint("product_id", "key", name="uq_product_attribute"),
    )

    op.create_table(
        "provider_product_attributes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "provider_product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("value_type", sa.String(length=50), nullable=False, server_default="string"),
        sa.UniqueConstraint("provider_product_id", "key", name="uq_provider_product_attribute"),
    )

    op.create_table(
        "product_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_index(
        "ix_products_search_vector",
        "products",
        [
            sa.text(
                "to_tsvector('simple', coalesce(sku,'') || ' ' || coalesce(name,'') || ' ' || coalesce(description,''))"
            )
        ],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_products_name_trgm",
        "products",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_products_sku_trgm",
        "products",
        ["sku"],
        postgresql_using="gin",
        postgresql_ops={"sku": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_products_sku_trgm", table_name="products")
    op.drop_index("ix_products_name_trgm", table_name="products")
    op.drop_index("ix_products_search_vector", table_name="products")
    op.drop_table("product_images")
    op.drop_table("provider_product_attributes")
    op.drop_table("product_attributes")
    op.drop_table("provider_products")
    op.drop_table("product_categories")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("brands")
    op.drop_table("providers")
    op.execute('DROP EXTENSION IF EXISTS "pg_trgm";')
