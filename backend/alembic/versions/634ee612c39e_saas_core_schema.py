"""saas_core_schema

Revision ID: 634ee612c39e
Revises: 542f89e1892a
Create Date: 2026-01-19 15:24:51.094856

Purpose:
- Create the SaaS core schema tables.
- Be safe on fresh databases where audit_logs does not yet exist.
- Preserve the original intent of dropping the audit_logs.id server default,
  but only do it when the table/column actually exists.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "634ee612c39e"
down_revision = "542f89e1892a"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name, schema="public")


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name, schema="public"):
        return False
    columns = inspector.get_columns(table_name, schema="public")
    return any(col["name"] == column_name for col in columns)


def _drop_audit_logs_id_default_if_present() -> None:
    if not _table_exists("audit_logs"):
        return
    if not _column_exists("audit_logs", "id"):
        return

    op.alter_column(
        "audit_logs",
        "id",
        existing_type=sa.VARCHAR(length=36),
        server_default=None,
        existing_nullable=False,
        schema="public",
    )


def _restore_audit_logs_id_default_if_present() -> None:
    if not _table_exists("audit_logs"):
        return
    if not _column_exists("audit_logs", "id"):
        return

    op.alter_column(
        "audit_logs",
        "id",
        existing_type=sa.VARCHAR(length=36),
        server_default=sa.text("(gen_random_uuid())::text"),
        existing_nullable=False,
        schema="public",
    )


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        op.f("ix_permissions_code"),
        "permissions",
        ["code"],
        unique=True,
        schema="public",
    )

    op.create_table(
        "tenants",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default="false", nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        op.f("ix_users_email"),
        "users",
        ["email"],
        unique=True,
        schema="public",
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["public.tenants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),
        schema="public",
    )
    op.create_index(
        op.f("ix_roles_tenant_id"),
        "roles",
        ["tenant_id"],
        unique=False,
        schema="public",
    )

    op.create_table(
        "tenant_users",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("is_owner", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["public.tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["public.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "user_id"),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_tenant_users_tenant_user"),
        schema="public",
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("permission_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["public.permissions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["role_id"], ["public.roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions"),
        schema="public",
    )

    op.create_table(
        "tenant_user_roles",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["public.roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["public.tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["public.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "user_id", "role_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "user_id",
            "role_id",
            name="uq_tenant_user_roles",
        ),
        schema="public",
    )

    _drop_audit_logs_id_default_if_present()


def downgrade() -> None:
    _restore_audit_logs_id_default_if_present()

    op.drop_table("tenant_user_roles", schema="public")
    op.drop_table("role_permissions", schema="public")
    op.drop_table("tenant_users", schema="public")
    op.drop_index(op.f("ix_roles_tenant_id"), table_name="roles", schema="public")
    op.drop_table("roles", schema="public")
    op.drop_index(op.f("ix_users_email"), table_name="users", schema="public")
    op.drop_table("users", schema="public")
    op.drop_table("tenants", schema="public")
    op.drop_index(
        op.f("ix_permissions_code"), table_name="permissions", schema="public"
    )
    op.drop_table("permissions", schema="public")
