"""add product_id to invoices

Revision ID: 20260331_02
Revises: e8407bd3faa3
Create Date: 2026-03-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260331_02"
down_revision: Union[str, None] = "e8407bd3faa3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("product_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_invoices_product_id_products",
        "invoices",
        "products",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_invoices_product_id_products", "invoices", type_="foreignkey")
    op.drop_column("invoices", "product_id")
