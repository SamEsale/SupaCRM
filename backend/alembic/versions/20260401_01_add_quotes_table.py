"""add quotes table

Revision ID: 20260401_01
Revises: 20260331_02
Create Date: 2026-04-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260401_01"
down_revision: Union[str, None] = "20260331_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quotes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("number", sa.String(length=50), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("contact_id", sa.String(length=36), nullable=True),
        sa.Column("deal_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number", name="uq_quotes_number"),
        sa.CheckConstraint(
            "status in ('draft', 'sent', 'accepted', 'rejected', 'expired')",
            name="ck_quotes_status_valid",
        ),
        sa.CheckConstraint(
            "expiry_date >= issue_date",
            name="ck_quotes_expiry_date_gte_issue_date",
        ),
        sa.CheckConstraint(
            "currency = upper(currency) AND char_length(currency) = 3",
            name="ck_quotes_currency_iso3_upper",
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name="ck_quotes_total_amount_nonnegative",
        ),
    )

    op.create_index("ix_quotes_tenant_id", "quotes", ["tenant_id"], unique=False)
    op.create_index("ix_quotes_number", "quotes", ["number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quotes_number", table_name="quotes")
    op.drop_index("ix_quotes_tenant_id", table_name="quotes")
    op.drop_table("quotes")

