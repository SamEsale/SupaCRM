"""add audit logs table

Revision ID: 20260413_05
Revises: 20260413_04
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260413_05"
down_revision: Union[str, None] = "20260413_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name, schema="public")


def upgrade() -> None:
    if not _table_exists("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=64), nullable=False),
            sa.Column("actor_user_id", sa.String(length=36), nullable=True),
            sa.Column("actor_ip", sa.String(length=64), nullable=True),
            sa.Column("request_id", sa.String(length=64), nullable=True),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("resource", sa.String(length=128), nullable=True),
            sa.Column("resource_id", sa.String(length=64), nullable=True),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["tenant_id"], ["public.tenants.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            schema="public",
        )

        op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"], schema="public")
        op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], schema="public")
        op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"], schema="public")
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"], schema="public")
        op.create_index("ix_audit_logs_resource", "audit_logs", ["resource"], schema="public")
        op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"], schema="public")

    op.execute("ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.audit_logs FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation ON public.audit_logs;")
    op.execute(
        """
        CREATE POLICY audit_logs_tenant_isolation
        ON public.audit_logs
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation ON public.audit_logs;")
    op.execute("ALTER TABLE public.audit_logs NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.audit_logs DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_audit_logs_resource_id", table_name="audit_logs", schema="public")
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs", schema="public")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs", schema="public")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs", schema="public")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs", schema="public")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs", schema="public")
    op.drop_table("audit_logs", schema="public")
