"""add_core_constraints

Revision ID: bb602ef6a38b
Revises: 634ee612c39e
Create Date: 2026-01-19

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bb602ef6a38b"
down_revision = "634ee612c39e"
branch_labels = None
depends_on = None


def _constraint_exists(conn, conname: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"),
            {"n": conname},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()

    # uq_role_permissions on role_permissions(role_id, permission_id)
    if not _constraint_exists(conn, "uq_role_permissions"):
        op.create_unique_constraint(
            "uq_role_permissions",
            "role_permissions",
            ["role_id", "permission_id"],
        )

    # uq_tenant_user_roles on tenant_user_roles(tenant_id, user_id, role_id)
    if not _constraint_exists(conn, "uq_tenant_user_roles"):
        op.create_unique_constraint(
            "uq_tenant_user_roles",
            "tenant_user_roles",
            ["tenant_id", "user_id", "role_id"],
        )

    # uq_tenant_users_tenant_user on tenant_users(tenant_id, user_id)
    if not _constraint_exists(conn, "uq_tenant_users_tenant_user"):
        op.create_unique_constraint(
            "uq_tenant_users_tenant_user",
            "tenant_users",
            ["tenant_id", "user_id"],
        )


def downgrade() -> None:
    # drop in reverse order if they exist
    conn = op.get_bind()

    if _constraint_exists(conn, "uq_tenant_users_tenant_user"):
        op.drop_constraint("uq_tenant_users_tenant_user", "tenant_users", type_="unique")

    if _constraint_exists(conn, "uq_tenant_user_roles"):
        op.drop_constraint("uq_tenant_user_roles", "tenant_user_roles", type_="unique")

    if _constraint_exists(conn, "uq_role_permissions"):
        op.drop_constraint("uq_role_permissions", "role_permissions", type_="unique")
