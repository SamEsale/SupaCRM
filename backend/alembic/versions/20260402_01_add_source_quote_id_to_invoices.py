"""add source_quote_id to invoices

Revision ID: 20260402_01
Revises: 20260401_01
Create Date: 2026-04-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_01"
down_revision: Union[str, None] = "20260401_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("source_quote_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_invoices_source_quote_id_quotes",
        "invoices",
        "quotes",
        ["source_quote_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_invoices_source_quote_id", "invoices", ["source_quote_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_invoices_source_quote_id", table_name="invoices")
    op.drop_constraint("fk_invoices_source_quote_id_quotes", "invoices", type_="foreignkey")
    op.drop_column("invoices", "source_quote_id")
