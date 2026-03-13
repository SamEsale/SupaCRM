"""baseline

Revision ID: 542f89e1892a
Revises: 
Create Date: 2026-01-16

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "542f89e1892a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # IMPORTANT:
    # Postgres will NOT allow altering a column type while an RLS policy
    # references that column. So we drop policy/policies, alter, recreate.
    # ------------------------------------------------------------------

    # Drop any known variants that may exist from earlier scripts/runs
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation ON public.audit_logs;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation_select ON public.audit_logs;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation_insert ON public.audit_logs;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation_update ON public.audit_logs;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation_delete ON public.audit_logs;")

    # ---- Your autogenerate changes (keep what matters) ----
    # If your DB has tenant_id as VARCHAR(36) but model is String(64),
    # this is the change Alembic detected.
    op.alter_column(
        "audit_logs",
        "tenant_id",
        existing_type=sa.VARCHAR(length=36),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    # Re-create ONE clean policy that covers all operations
    # (SELECT/INSERT/UPDATE/DELETE) using app.tenant_id GUC
    op.execute(
        """
        CREATE POLICY audit_logs_tenant_isolation
        ON public.audit_logs
        FOR ALL
        USING (tenant_id = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
        """
    )


def downgrade() -> None:
    # Drop policy first to allow reverting the column type
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation ON public.audit_logs;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation_select ON public.audit_logs;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation_insert ON public.audit_logs;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation_update ON public.audit_logs;")
    op.execute("DROP POLICY IF EXISTS audit_logs_tenant_isolation_delete ON public.audit_logs;")

    # Revert tenant_id back to VARCHAR(36)
    op.alter_column(
        "audit_logs",
        "tenant_id",
        existing_type=sa.String(length=64),
        type_=sa.VARCHAR(length=36),
        existing_nullable=False,
    )

    # Re-create policy again (optional, but keeps DB consistent after downgrade)
    op.execute(
        """
        CREATE POLICY audit_logs_tenant_isolation
        ON public.audit_logs
        FOR ALL
        USING (tenant_id = current_setting('app.tenant_id', true))
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
        """
    )
