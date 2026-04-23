"""complete marketing and social foundation

Revision ID: 20260420_01
Revises: 20260414_03
Create Date: 2026-04-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260420_01"
down_revision: Union[str, None] = "20260414_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "social_integration_settings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.add_column(
        "marketing_campaigns",
        sa.Column(
            "audience_type",
            sa.String(length=32),
            nullable=False,
            server_default="all_contacts",
        ),
    )
    op.add_column(
        "marketing_campaigns",
        sa.Column("blocked_reason", sa.Text(), nullable=True),
    )

    op.execute(
        """
        update public.marketing_campaigns
        set audience_type = case
            when target_contact_id is not null then 'target_contact_only'
            when target_company_id is not null then 'target_company_contacts'
            else 'all_contacts'
        end
        """
    )

    op.drop_constraint("ck_marketing_campaigns_status_valid", "marketing_campaigns", type_="check")
    op.create_check_constraint(
        "ck_marketing_campaigns_status_valid",
        "marketing_campaigns",
        "status in ('draft', 'scheduled', 'sending', 'completed', 'failed', 'blocked')",
    )
    op.create_check_constraint(
        "ck_marketing_campaigns_audience_type_valid",
        "marketing_campaigns",
        "audience_type in ('all_contacts', 'target_company_contacts', 'target_contact_only')",
    )

    op.create_table(
        "marketing_campaign_executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="blocked"),
        sa.Column("initiated_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("total_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_recipients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("batch_size", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("queued_batch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queue_job_id", sa.String(length=64), nullable=True),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status in ('sending', 'completed', 'failed', 'blocked')",
            name="ck_marketing_campaign_executions_status_valid",
        ),
    )
    op.create_index(
        "ix_marketing_campaign_executions_tenant_id",
        "marketing_campaign_executions",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_marketing_campaign_executions_campaign_id",
        "marketing_campaign_executions",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_marketing_campaign_executions_queue_job_id",
        "marketing_campaign_executions",
        ["queue_job_id"],
        unique=False,
    )

    op.create_table(
        "marketing_campaign_execution_recipients",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("execution_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("contact_id", sa.String(length=36), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("batch_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["marketing_campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["execution_id"], ["marketing_campaign_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "execution_id",
            "email",
            name="uq_marketing_campaign_execution_recipients_execution_email",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'sent', 'failed', 'blocked')",
            name="ck_marketing_campaign_execution_recipients_status_valid",
        ),
    )
    op.create_index(
        "ix_marketing_campaign_execution_recipients_tenant_id",
        "marketing_campaign_execution_recipients",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_marketing_campaign_execution_recipients_execution_id",
        "marketing_campaign_execution_recipients",
        ["execution_id"],
        unique=False,
    )
    op.create_index(
        "ix_marketing_campaign_execution_recipients_campaign_id",
        "marketing_campaign_execution_recipients",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_marketing_campaign_execution_recipients_contact_id",
        "marketing_campaign_execution_recipients",
        ["contact_id"],
        unique=False,
    )

    op.execute("ALTER TABLE public.marketing_campaign_executions ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.marketing_campaign_executions FORCE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS marketing_campaign_executions_tenant_isolation ON public.marketing_campaign_executions;"
    )
    op.execute(
        """
        CREATE POLICY marketing_campaign_executions_tenant_isolation
        ON public.marketing_campaign_executions
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )

    op.execute("ALTER TABLE public.marketing_campaign_execution_recipients ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.marketing_campaign_execution_recipients FORCE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS marketing_campaign_execution_recipients_tenant_isolation ON public.marketing_campaign_execution_recipients;"
    )
    op.execute(
        """
        CREATE POLICY marketing_campaign_execution_recipients_tenant_isolation
        ON public.marketing_campaign_execution_recipients
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS marketing_campaign_execution_recipients_tenant_isolation ON public.marketing_campaign_execution_recipients;"
    )
    op.execute("ALTER TABLE public.marketing_campaign_execution_recipients NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.marketing_campaign_execution_recipients DISABLE ROW LEVEL SECURITY;")
    op.execute(
        "DROP POLICY IF EXISTS marketing_campaign_executions_tenant_isolation ON public.marketing_campaign_executions;"
    )
    op.execute("ALTER TABLE public.marketing_campaign_executions NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.marketing_campaign_executions DISABLE ROW LEVEL SECURITY;")

    op.drop_index(
        "ix_marketing_campaign_execution_recipients_contact_id",
        table_name="marketing_campaign_execution_recipients",
    )
    op.drop_index(
        "ix_marketing_campaign_execution_recipients_campaign_id",
        table_name="marketing_campaign_execution_recipients",
    )
    op.drop_index(
        "ix_marketing_campaign_execution_recipients_execution_id",
        table_name="marketing_campaign_execution_recipients",
    )
    op.drop_index(
        "ix_marketing_campaign_execution_recipients_tenant_id",
        table_name="marketing_campaign_execution_recipients",
    )
    op.drop_table("marketing_campaign_execution_recipients")

    op.drop_index("ix_marketing_campaign_executions_queue_job_id", table_name="marketing_campaign_executions")
    op.drop_index("ix_marketing_campaign_executions_campaign_id", table_name="marketing_campaign_executions")
    op.drop_index("ix_marketing_campaign_executions_tenant_id", table_name="marketing_campaign_executions")
    op.drop_table("marketing_campaign_executions")

    op.drop_constraint("ck_marketing_campaigns_audience_type_valid", "marketing_campaigns", type_="check")
    op.drop_constraint("ck_marketing_campaigns_status_valid", "marketing_campaigns", type_="check")
    op.create_check_constraint(
        "ck_marketing_campaigns_status_valid",
        "marketing_campaigns",
        "status in ('draft', 'scheduled')",
    )
    op.drop_column("marketing_campaigns", "blocked_reason")
    op.drop_column("marketing_campaigns", "audience_type")

    op.drop_column("tenants", "social_integration_settings")
