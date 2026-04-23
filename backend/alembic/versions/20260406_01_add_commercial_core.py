"""add commercial core

Revision ID: 20260406_01
Revises: 20260405_01
Create Date: 2026-04-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "20260406_01"
down_revision: Union[str, None] = "20260405_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COMMERCIAL_TABLES: tuple[str, ...] = (
    "commercial_subscriptions",
    "commercial_billing_cycles",
    "commercial_billing_events",
)


def _policy_name(table: str) -> str:
    return f"{table}_tenant_isolation"


def upgrade() -> None:
    op.create_table(
        "commercial_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="stripe"),
        sa.Column("provider_price_id", sa.String(length=128), nullable=True),
        sa.Column("billing_interval", sa.String(length=16), nullable=False),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("trial_days", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("grace_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("features", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_commercial_plans_code"),
    )
    op.create_index("ix_commercial_plans_code", "commercial_plans", ["code"], unique=False)

    op.create_table(
        "commercial_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("plan_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="stripe"),
        sa.Column("provider_customer_id", sa.String(length=128), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("commercial_state", sa.String(length=32), nullable=False, server_default="trial"),
        sa.Column("state_reason", sa.String(length=255), nullable=True),
        sa.Column("trial_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("grace_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["commercial_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_commercial_subscriptions_tenant_id"),
        sa.UniqueConstraint("provider_subscription_id", name="uq_commercial_subscriptions_provider_subscription_id"),
    )
    op.create_index("ix_commercial_subscriptions_tenant_id", "commercial_subscriptions", ["tenant_id"], unique=False)
    op.create_index("ix_commercial_subscriptions_plan_id", "commercial_subscriptions", ["plan_id"], unique=False)
    op.create_index("ix_commercial_subscriptions_provider_customer_id", "commercial_subscriptions", ["provider_customer_id"], unique=False)

    op.create_table(
        "commercial_billing_cycles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("subscription_id", sa.String(length=36), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("period_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("invoice_id", sa.String(length=36), nullable=True),
        sa.Column("provider_event_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["commercial_subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subscription_id", "cycle_number", name="uq_commercial_billing_cycles_subscription_cycle"),
    )
    op.create_index("ix_commercial_billing_cycles_tenant_id", "commercial_billing_cycles", ["tenant_id"], unique=False)
    op.create_index("ix_commercial_billing_cycles_subscription_id", "commercial_billing_cycles", ["subscription_id"], unique=False)
    op.create_index("ix_commercial_billing_cycles_invoice_id", "commercial_billing_cycles", ["invoice_id"], unique=False)
    op.create_index("ix_commercial_billing_cycles_provider_event_id", "commercial_billing_cycles", ["provider_event_id"], unique=False)

    op.create_table(
        "commercial_billing_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("subscription_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("action_taken", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["commercial_subscriptions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_event_id", name="uq_commercial_billing_events_provider_external_event"),
    )
    op.create_index("ix_commercial_billing_events_tenant_id", "commercial_billing_events", ["tenant_id"], unique=False)
    op.create_index("ix_commercial_billing_events_subscription_id", "commercial_billing_events", ["subscription_id"], unique=False)
    op.create_index("ix_commercial_billing_events_event_type", "commercial_billing_events", ["event_type"], unique=False)

    op.add_column("invoices", sa.Column("subscription_id", sa.String(length=36), nullable=True))
    op.add_column("invoices", sa.Column("billing_cycle_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_invoices_subscription_id_commercial_subscriptions",
        "invoices",
        "commercial_subscriptions",
        ["subscription_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_invoices_billing_cycle_id_commercial_billing_cycles",
        "invoices",
        "commercial_billing_cycles",
        ["billing_cycle_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_invoices_subscription_id", "invoices", ["subscription_id"], unique=False)
    op.create_index("ix_invoices_billing_cycle_id", "invoices", ["billing_cycle_id"], unique=False)

    for table in COMMERCIAL_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY;")
        policy_name = _policy_name(table)
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON public.{table};")
        op.execute(
            f"""
            CREATE POLICY {policy_name}
            ON public.{table}
            USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
            WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
            """
        )


def downgrade() -> None:
    for table in COMMERCIAL_TABLES:
        policy_name = _policy_name(table)
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON public.{table};")
        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_invoices_billing_cycle_id", table_name="invoices")
    op.drop_index("ix_invoices_subscription_id", table_name="invoices")
    op.drop_constraint("fk_invoices_billing_cycle_id_commercial_billing_cycles", "invoices", type_="foreignkey")
    op.drop_constraint("fk_invoices_subscription_id_commercial_subscriptions", "invoices", type_="foreignkey")
    op.drop_column("invoices", "billing_cycle_id")
    op.drop_column("invoices", "subscription_id")

    op.drop_index("ix_commercial_billing_events_event_type", table_name="commercial_billing_events")
    op.drop_index("ix_commercial_billing_events_subscription_id", table_name="commercial_billing_events")
    op.drop_index("ix_commercial_billing_events_tenant_id", table_name="commercial_billing_events")
    op.drop_table("commercial_billing_events")

    op.drop_index("ix_commercial_billing_cycles_provider_event_id", table_name="commercial_billing_cycles")
    op.drop_index("ix_commercial_billing_cycles_invoice_id", table_name="commercial_billing_cycles")
    op.drop_index("ix_commercial_billing_cycles_subscription_id", table_name="commercial_billing_cycles")
    op.drop_index("ix_commercial_billing_cycles_tenant_id", table_name="commercial_billing_cycles")
    op.drop_table("commercial_billing_cycles")

    op.drop_index("ix_commercial_subscriptions_provider_customer_id", table_name="commercial_subscriptions")
    op.drop_index("ix_commercial_subscriptions_plan_id", table_name="commercial_subscriptions")
    op.drop_index("ix_commercial_subscriptions_tenant_id", table_name="commercial_subscriptions")
    op.drop_table("commercial_subscriptions")

    op.drop_index("ix_commercial_plans_code", table_name="commercial_plans")
    op.drop_table("commercial_plans")

