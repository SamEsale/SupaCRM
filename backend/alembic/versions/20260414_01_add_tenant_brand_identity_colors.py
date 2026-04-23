"""add tenant brand identity colors

Revision ID: 20260414_01
Revises: 20260413_05
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260414_01"
down_revision: Union[str, None] = "20260413_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("brand_primary_color", sa.String(length=7), nullable=True))
    op.add_column("tenants", sa.Column("brand_secondary_color", sa.String(length=7), nullable=True))
    op.add_column("tenants", sa.Column("sidebar_background_color", sa.String(length=7), nullable=True))
    op.add_column("tenants", sa.Column("sidebar_text_color", sa.String(length=7), nullable=True))

    op.create_check_constraint(
        "ck_tenants_brand_primary_color_hex",
        "tenants",
        "brand_primary_color is null or brand_primary_color ~ '^#[0-9A-Fa-f]{6}$'",
    )
    op.create_check_constraint(
        "ck_tenants_brand_secondary_color_hex",
        "tenants",
        "brand_secondary_color is null or brand_secondary_color ~ '^#[0-9A-Fa-f]{6}$'",
    )
    op.create_check_constraint(
        "ck_tenants_sidebar_background_color_hex",
        "tenants",
        "sidebar_background_color is null or sidebar_background_color ~ '^#[0-9A-Fa-f]{6}$'",
    )
    op.create_check_constraint(
        "ck_tenants_sidebar_text_color_hex",
        "tenants",
        "sidebar_text_color is null or sidebar_text_color ~ '^#[0-9A-Fa-f]{6}$'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tenants_sidebar_text_color_hex", "tenants", type_="check")
    op.drop_constraint("ck_tenants_sidebar_background_color_hex", "tenants", type_="check")
    op.drop_constraint("ck_tenants_brand_secondary_color_hex", "tenants", type_="check")
    op.drop_constraint("ck_tenants_brand_primary_color_hex", "tenants", type_="check")

    op.drop_column("tenants", "sidebar_text_color")
    op.drop_column("tenants", "sidebar_background_color")
    op.drop_column("tenants", "brand_secondary_color")
    op.drop_column("tenants", "brand_primary_color")
