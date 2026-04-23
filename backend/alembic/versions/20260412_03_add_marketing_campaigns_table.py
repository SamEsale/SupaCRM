"""add marketing campaigns table

Revision ID: 20260412_03
Revises: 20260412_02
Create Date: 2026-04-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260412_03"
down_revision: Union[str, None] = "20260412_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("audience_description", sa.Text(), nullable=True),
        sa.Column("target_company_id", sa.String(length=36), nullable=True),
        sa.Column("target_contact_id", sa.String(length=36), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("message_body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "channel in ('email', 'whatsapp')",
            name="ck_marketing_campaigns_channel_valid",
        ),
        sa.CheckConstraint(
            "status in ('draft', 'scheduled')",
            name="ck_marketing_campaigns_status_valid",
        ),
    )
    op.create_index(
        "ix_marketing_campaigns_tenant_id",
        "marketing_campaigns",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_marketing_campaigns_status",
        "marketing_campaigns",
        ["status"],
        unique=False,
    )

    op.execute("ALTER TABLE public.marketing_campaigns ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.marketing_campaigns FORCE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS marketing_campaigns_tenant_isolation ON public.marketing_campaigns;"
    )
    op.execute(
        """
        CREATE POLICY marketing_campaigns_tenant_isolation
        ON public.marketing_campaigns
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS marketing_campaigns_tenant_isolation ON public.marketing_campaigns;")
    op.execute("ALTER TABLE public.marketing_campaigns NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.marketing_campaigns DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_marketing_campaigns_status", table_name="marketing_campaigns")
    op.drop_index("ix_marketing_campaigns_tenant_id", table_name="marketing_campaigns")
    op.drop_table("marketing_campaigns")
