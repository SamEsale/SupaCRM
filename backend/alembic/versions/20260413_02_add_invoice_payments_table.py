"""add invoice payments table

Revision ID: 20260413_02
Revises: 20260413_01
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260413_02"
down_revision: Union[str, None] = "20260413_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice_payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "method in ('bank_transfer', 'cash', 'card_manual', 'other')",
            name="ck_invoice_payments_method_valid",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'failed', 'cancelled')",
            name="ck_invoice_payments_status_valid",
        ),
        sa.CheckConstraint("amount > 0", name="ck_invoice_payments_amount_positive"),
    )
    op.create_index("ix_invoice_payments_tenant_id", "invoice_payments", ["tenant_id"], unique=False)
    op.create_index("ix_invoice_payments_invoice_id", "invoice_payments", ["invoice_id"], unique=False)
    op.create_index("ix_invoice_payments_status", "invoice_payments", ["status"], unique=False)
    op.create_index("ix_invoice_payments_payment_date", "invoice_payments", ["payment_date"], unique=False)

    op.execute("ALTER TABLE public.invoice_payments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.invoice_payments FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS invoice_payments_tenant_isolation ON public.invoice_payments;")
    op.execute(
        """
        CREATE POLICY invoice_payments_tenant_isolation
        ON public.invoice_payments
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS invoice_payments_tenant_isolation ON public.invoice_payments;")
    op.execute("ALTER TABLE public.invoice_payments NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.invoice_payments DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_invoice_payments_payment_date", table_name="invoice_payments")
    op.drop_index("ix_invoice_payments_status", table_name="invoice_payments")
    op.drop_index("ix_invoice_payments_invoice_id", table_name="invoice_payments")
    op.drop_index("ix_invoice_payments_tenant_id", table_name="invoice_payments")
    op.drop_table("invoice_payments")
