"""add source_deal_id to quotes

Revision ID: 20260402_02
Revises: 20260402_01
Create Date: 2026-04-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260402_02"
down_revision: Union[str, None] = "20260402_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quotes", sa.Column("source_deal_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_quotes_source_deal_id_deals",
        "quotes",
        "deals",
        ["source_deal_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_quotes_source_deal_id", "quotes", ["source_deal_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quotes_source_deal_id", table_name="quotes")
    op.drop_constraint("fk_quotes_source_deal_id_deals", "quotes", type_="foreignkey")
    op.drop_column("quotes", "source_deal_id")
