"""add_auth_token_state

Revision ID: 6c2b5f9a8d13
Revises: 3ff6222d94c7
Create Date: 2026-03-12
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6c2b5f9a8d13"
down_revision = "3ff6222d94c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_credentials",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "user_credentials",
        sa.Column("refresh_token_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "user_credentials",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_credentials",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_credentials",
        sa.Column("last_failed_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.String(length=36), nullable=True),
        sa.Column("revoked_reason", sa.String(length=255), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_refresh_tokens_user_id", "auth_refresh_tokens", ["user_id"], unique=False)
    op.create_index("ix_auth_refresh_tokens_tenant_id", "auth_refresh_tokens", ["tenant_id"], unique=False)
    op.create_index("ix_auth_refresh_tokens_token_hash", "auth_refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_auth_refresh_tokens_family_id", "auth_refresh_tokens", ["family_id"], unique=False)
    op.create_index("ix_auth_refresh_tokens_expires_at", "auth_refresh_tokens", ["expires_at"], unique=False)

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"], unique=False)
    op.create_index("ix_password_reset_tokens_tenant_id", "password_reset_tokens", ["tenant_id"], unique=False)
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"], unique=False)

    op.execute("ALTER TABLE public.auth_refresh_tokens ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.auth_refresh_tokens FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.password_reset_tokens FORCE ROW LEVEL SECURITY;")

    op.execute("DROP POLICY IF EXISTS auth_refresh_tokens_tenant_isolation ON public.auth_refresh_tokens;")
    op.execute(
        """
        CREATE POLICY auth_refresh_tokens_tenant_isolation
        ON public.auth_refresh_tokens
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )

    op.execute("DROP POLICY IF EXISTS password_reset_tokens_tenant_isolation ON public.password_reset_tokens;")
    op.execute(
        """
        CREATE POLICY password_reset_tokens_tenant_isolation
        ON public.password_reset_tokens
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.auth_refresh_tokens TO app_user;
                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.password_reset_tokens TO app_user;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS auth_refresh_tokens_tenant_isolation ON public.auth_refresh_tokens;")
    op.execute("DROP POLICY IF EXISTS password_reset_tokens_tenant_isolation ON public.password_reset_tokens;")

    op.execute("ALTER TABLE public.auth_refresh_tokens NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.auth_refresh_tokens DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.password_reset_tokens NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.password_reset_tokens DISABLE ROW LEVEL SECURITY;")

    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_tenant_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")

    op.drop_index("ix_auth_refresh_tokens_expires_at", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_family_id", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_token_hash", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_tenant_id", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_user_id", table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")

    op.drop_column("user_credentials", "last_failed_login_at")
    op.drop_column("user_credentials", "last_login_at")
    op.drop_column("user_credentials", "locked_until")
    op.drop_column("user_credentials", "refresh_token_version")
    op.drop_column("user_credentials", "failed_login_attempts")
