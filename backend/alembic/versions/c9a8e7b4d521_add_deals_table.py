"""add_deals_table

Revision ID: c9a8e7b4d521
Revises: ab3d91f1c2e4
Create Date: 2026-03-24 10:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c9a8e7b4d521"
down_revision = "ab3d91f1c2e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("contact_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("stage", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("expected_close_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("amount >= 0", name="ck_deals_amount_nonnegative"),
        sa.CheckConstraint(
            "currency = upper(currency) AND char_length(currency) = 3",
            name="ck_deals_currency_iso3_upper",
        ),
        sa.CheckConstraint(
            "stage in ('lead', 'qualified', 'proposal', 'estimate', 'negotiation', 'won', 'lost')",
            name="ck_deals_stage_valid",
        ),
        sa.CheckConstraint(
            "status in ('open', 'in progress', 'won', 'lost', 'archived')",
            name="ck_deals_status_valid",
        ),
    )
    op.create_index(op.f("ix_deals_tenant_id"), "deals", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_deals_tenant_id"), table_name="deals")
    op.drop_table("deals")