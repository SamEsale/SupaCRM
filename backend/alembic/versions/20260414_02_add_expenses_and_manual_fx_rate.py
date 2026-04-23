"""add expenses and manual fx rate fields

Revision ID: 20260414_02
Revises: 20260414_01
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260414_02"
down_revision: Union[str, None] = "20260414_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("secondary_currency_rate", sa.Numeric(18, 6), nullable=True))
    op.add_column("tenants", sa.Column("secondary_currency_rate_source", sa.String(length=64), nullable=True))
    op.add_column("tenants", sa.Column("secondary_currency_rate_as_of", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "ck_tenants_secondary_currency_rate_positive",
        "tenants",
        "secondary_currency_rate is null or secondary_currency_rate > 0",
    )

    op.create_table(
        "expenses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("vendor_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status in ('draft', 'submitted', 'approved', 'paid')",
            name="ck_expenses_status_valid",
        ),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_expenses_currency_length"),
    )
    op.create_index("ix_expenses_tenant_id", "expenses", ["tenant_id"], unique=False)
    op.create_index("ix_expenses_status", "expenses", ["status"], unique=False)
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"], unique=False)

    op.execute("ALTER TABLE public.expenses ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.expenses FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS expenses_tenant_isolation ON public.expenses;")
    op.execute(
        """
        CREATE POLICY expenses_tenant_isolation
        ON public.expenses
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS expenses_tenant_isolation ON public.expenses;")
    op.execute("ALTER TABLE public.expenses NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.expenses DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_expenses_expense_date", table_name="expenses")
    op.drop_index("ix_expenses_status", table_name="expenses")
    op.drop_index("ix_expenses_tenant_id", table_name="expenses")
    op.drop_table("expenses")

    op.drop_constraint("ck_tenants_secondary_currency_rate_positive", "tenants", type_="check")
    op.drop_column("tenants", "secondary_currency_rate_as_of")
    op.drop_column("tenants", "secondary_currency_rate_source")
    op.drop_column("tenants", "secondary_currency_rate")
