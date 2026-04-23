"""add tenant company settings

Revision ID: 20260413_03
Revises: 20260413_02
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260413_03"
down_revision: Union[str, None] = "20260413_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("legal_name", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("address_line_1", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("address_line_2", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("city", sa.String(length=120), nullable=True))
    op.add_column("tenants", sa.Column("state_region", sa.String(length=120), nullable=True))
    op.add_column("tenants", sa.Column("postal_code", sa.String(length=40), nullable=True))
    op.add_column("tenants", sa.Column("country", sa.String(length=120), nullable=True))
    op.add_column("tenants", sa.Column("vat_number", sa.String(length=64), nullable=True))
    op.add_column(
        "tenants",
        sa.Column("default_currency", sa.String(length=3), nullable=False, server_default="USD"),
    )
    op.add_column("tenants", sa.Column("secondary_currency", sa.String(length=3), nullable=True))

    op.create_check_constraint(
        "ck_tenants_secondary_currency_distinct",
        "tenants",
        "secondary_currency is null or secondary_currency <> default_currency",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tenants_secondary_currency_distinct", "tenants", type_="check")
    op.drop_column("tenants", "secondary_currency")
    op.drop_column("tenants", "default_currency")
    op.drop_column("tenants", "vat_number")
    op.drop_column("tenants", "country")
    op.drop_column("tenants", "postal_code")
    op.drop_column("tenants", "state_region")
    op.drop_column("tenants", "city")
    op.drop_column("tenants", "address_line_2")
    op.drop_column("tenants", "address_line_1")
    op.drop_column("tenants", "legal_name")
