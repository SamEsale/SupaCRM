"""baseline

Revision ID: 542f89e1892a
Revises:
Create Date: 2026-03-xx

Purpose:
- Make the original baseline migration safe on both:
  1. legacy databases where audit_logs already exists, and
  2. fresh databases where audit_logs does not yet exist.

The previous version assumed audit_logs already existed and tried to alter
audit_logs.tenant_id unconditionally. That breaks clean bootstrap because the
table is created later in the migration chain.

This version is intentionally idempotent:
- if audit_logs does not exist, upgrade() does nothing
- if audit_logs exists but tenant_id does not, upgrade() does nothing
- if the column already has the desired type, upgrade() leaves it alone
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "542f89e1892a"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name, schema="public")


def _column_info(table_name: str, column_name: str) -> dict | None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for column in inspector.get_columns(table_name, schema="public"):
        if column["name"] == column_name:
            return column
    return None


def _is_varchar_64(column_type: object) -> bool:
    if not isinstance(column_type, sa.String):
        return False
    return getattr(column_type, "length", None) == 64


def _drop_audit_logs_policy_if_exists() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_policy p
                JOIN pg_class c ON c.oid = p.polrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = 'audit_logs'
                  AND p.polname = 'audit_logs_tenant_isolation'
            ) THEN
                DROP POLICY audit_logs_tenant_isolation ON public.audit_logs;
            END IF;
        END
        $$;
        """
    )


def _recreate_audit_logs_policy_if_needed() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = 'audit_logs'
            ) THEN
                ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
                ALTER TABLE public.audit_logs FORCE ROW LEVEL SECURITY;
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_policy p
                JOIN pg_class c ON c.oid = p.polrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND c.relname = 'audit_logs'
                  AND p.polname = 'audit_logs_tenant_isolation'
            )
            AND EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'audit_logs'
                  AND column_name = 'tenant_id'
            ) THEN
                CREATE POLICY audit_logs_tenant_isolation
                ON public.audit_logs
                FOR ALL
                USING (tenant_id = current_setting('app.tenant_id', true)::varchar(64))
                WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::varchar(64));
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    # Fresh DB path:
    # audit_logs does not exist yet -> this baseline should be a no-op.
    if not _table_exists("audit_logs"):
        return

    tenant_id_column = _column_info("audit_logs", "tenant_id")
    if tenant_id_column is None:
        return

    if _is_varchar_64(tenant_id_column["type"]):
        return

    # If RLS policy exists, Postgres may block tenant_id type changes.
    _drop_audit_logs_policy_if_exists()

    op.alter_column(
        "audit_logs",
        "tenant_id",
        existing_type=sa.String(),
        type_=sa.String(length=64),
        existing_nullable=False,
        postgresql_using="tenant_id::varchar(64)",
        schema="public",
    )

    _recreate_audit_logs_policy_if_needed()


def downgrade() -> None:
    # Downgrade is intentionally conservative and safe:
    # only attempt reverse change if table + column exist and currently look like varchar(64).
    if not _table_exists("audit_logs"):
        return

    tenant_id_column = _column_info("audit_logs", "tenant_id")
    if tenant_id_column is None:
        return

    if not _is_varchar_64(tenant_id_column["type"]):
        return

    _drop_audit_logs_policy_if_exists()

    op.alter_column(
        "audit_logs",
        "tenant_id",
        existing_type=sa.String(length=64),
        type_=sa.String(length=36),
        existing_nullable=False,
        postgresql_using="left(tenant_id, 36)",
        schema="public",
    )

    _recreate_audit_logs_policy_if_needed()
