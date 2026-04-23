"""add support tickets table

Revision ID: 20260412_04
Revises: 20260412_03
Create Date: 2026-04-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260412_04"
down_revision: Union[str, None] = "20260412_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("contact_id", sa.String(length=36), nullable=True),
        sa.Column("assigned_to_user_id", sa.String(length=36), nullable=True),
        sa.Column("related_deal_id", sa.String(length=36), nullable=True),
        sa.Column("related_invoice_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_deal_id"], ["deals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status in ('open', 'in progress', 'waiting on customer', 'resolved', 'closed')",
            name="ck_support_tickets_status_valid",
        ),
        sa.CheckConstraint(
            "priority in ('low', 'medium', 'high', 'urgent')",
            name="ck_support_tickets_priority_valid",
        ),
        sa.CheckConstraint(
            "source in ('manual', 'email', 'whatsapp', 'phone', 'web')",
            name="ck_support_tickets_source_valid",
        ),
    )
    op.create_index("ix_support_tickets_tenant_id", "support_tickets", ["tenant_id"], unique=False)
    op.create_index("ix_support_tickets_status", "support_tickets", ["status"], unique=False)
    op.create_index("ix_support_tickets_priority", "support_tickets", ["priority"], unique=False)

    op.execute("ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.support_tickets FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS support_tickets_tenant_isolation ON public.support_tickets;")
    op.execute(
        """
        CREATE POLICY support_tickets_tenant_isolation
        ON public.support_tickets
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS support_tickets_tenant_isolation ON public.support_tickets;")
    op.execute("ALTER TABLE public.support_tickets NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.support_tickets DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_support_tickets_priority", table_name="support_tickets")
    op.drop_index("ix_support_tickets_status", table_name="support_tickets")
    op.drop_index("ix_support_tickets_tenant_id", table_name="support_tickets")
    op.drop_table("support_tickets")
