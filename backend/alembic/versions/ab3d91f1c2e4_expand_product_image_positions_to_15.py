"""expand product image positions to 15

Revision ID: ab3d91f1c2e4
Revises: 4df8236cede9
Create Date: 2026-03-23 14:15:00.000000
"""

from alembic import op


revision = "ab3d91f1c2e4"
down_revision = "4df8236cede9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.product_images
        DROP CONSTRAINT IF EXISTS ck_product_images_position_123
        """
    )

    op.execute(
        """
        ALTER TABLE public.product_images
        ADD CONSTRAINT ck_product_images_position_1_15
        CHECK (position >= 1 AND position <= 15)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.product_images
        DROP CONSTRAINT IF EXISTS ck_product_images_position_1_15
        """
    )

    op.execute(
        """
        ALTER TABLE public.product_images
        ADD CONSTRAINT ck_product_images_position_123
        CHECK (position in (1, 2, 3))
        """
    )