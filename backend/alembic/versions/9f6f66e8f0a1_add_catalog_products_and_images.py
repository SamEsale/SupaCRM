"""add catalog products and images

Revision ID: 9f6f66e8f0a1
Revises: 04b3f0195d54
Create Date: 2026-03-20 16:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "9f6f66e8f0a1"
down_revision = "04b3f0195d54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_products_tenant_sku"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_products_tenant_id_id"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    op.create_index("ix_products_tenant_id_is_active", "products", ["tenant_id", "is_active"])

    op.create_table(
        "product_images",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("file_key", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("position in (1, 2, 3)", name="ck_product_images_position_123"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "product_id"],
            ["products.tenant_id", "products.id"],
            ondelete="CASCADE",
            name="fk_product_images_tenant_product",
        ),
        sa.UniqueConstraint("tenant_id", "product_id", "position", name="uq_product_images_tenant_product_position"),
    )
    op.create_index("ix_product_images_tenant_id", "product_images", ["tenant_id"])
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])

    op.execute("ALTER TABLE public.products ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.products FORCE ROW LEVEL SECURITY")

    op.execute("ALTER TABLE public.product_images ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.product_images FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY products_select_policy
        ON public.products
        FOR SELECT
        USING (tenant_id = current_setting('app.tenant_id', true))
        """
    )
    op.execute(
        """
        CREATE POLICY products_insert_policy
        ON public.products
        FOR INSERT
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
        """
    )
    op.execute(
        """
        CREATE POLICY products_update_policy
        ON public.products
        FOR UPDATE
        USING (tenant_id = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
        """
    )
    op.execute(
        """
        CREATE POLICY products_delete_policy
        ON public.products
        FOR DELETE
        USING (tenant_id = current_setting('app.tenant_id', true))
        """
    )

    op.execute(
        """
        CREATE POLICY product_images_select_policy
        ON public.product_images
        FOR SELECT
        USING (tenant_id = current_setting('app.tenant_id', true))
        """
    )
    op.execute(
        """
        CREATE POLICY product_images_insert_policy
        ON public.product_images
        FOR INSERT
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
        """
    )
    op.execute(
        """
        CREATE POLICY product_images_update_policy
        ON public.product_images
        FOR UPDATE
        USING (tenant_id = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true))
        """
    )
    op.execute(
        """
        CREATE POLICY product_images_delete_policy
        ON public.product_images
        FOR DELETE
        USING (tenant_id = current_setting('app.tenant_id', true))
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS product_images_delete_policy ON public.product_images")
    op.execute("DROP POLICY IF EXISTS product_images_update_policy ON public.product_images")
    op.execute("DROP POLICY IF EXISTS product_images_insert_policy ON public.product_images")
    op.execute("DROP POLICY IF EXISTS product_images_select_policy ON public.product_images")

    op.execute("DROP POLICY IF EXISTS products_delete_policy ON public.products")
    op.execute("DROP POLICY IF EXISTS products_update_policy ON public.products")
    op.execute("DROP POLICY IF EXISTS products_insert_policy ON public.products")
    op.execute("DROP POLICY IF EXISTS products_select_policy ON public.products")

    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_index("ix_product_images_tenant_id", table_name="product_images")
    op.drop_table("product_images")

    op.drop_index("ix_products_tenant_id_is_active", table_name="products")
    op.drop_index("ix_products_tenant_id", table_name="products")
    op.drop_table("products")