"""enable_rls_for_roles_and_tenant_links

Revision ID: b834d7a56e0d
Revises: bb602ef6a38b
Create Date: 2026-01-28
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b834d7a56e0d"
down_revision = "bb602ef6a38b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable + force RLS on tenant-scoped tables
    op.execute("ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.roles FORCE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE public.tenant_users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.tenant_users FORCE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE public.tenant_user_roles ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.tenant_user_roles FORCE ROW LEVEL SECURITY;")

    # Policies (idempotent)
    op.execute("DROP POLICY IF EXISTS roles_tenant_isolation ON public.roles;")
    op.execute(
        """
        CREATE POLICY roles_tenant_isolation
        ON public.roles
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )

    op.execute("DROP POLICY IF EXISTS tenant_users_tenant_isolation ON public.tenant_users;")
    op.execute(
        """
        CREATE POLICY tenant_users_tenant_isolation
        ON public.tenant_users
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )

    op.execute("DROP POLICY IF EXISTS tenant_user_roles_tenant_isolation ON public.tenant_user_roles;")
    op.execute(
        """
        CREATE POLICY tenant_user_roles_tenant_isolation
        ON public.tenant_user_roles
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS roles_tenant_isolation ON public.roles;")
    op.execute("DROP POLICY IF EXISTS tenant_users_tenant_isolation ON public.tenant_users;")
    op.execute("DROP POLICY IF EXISTS tenant_user_roles_tenant_isolation ON public.tenant_user_roles;")

    op.execute("ALTER TABLE public.roles NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.roles DISABLE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE public.tenant_users NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.tenant_users DISABLE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE public.tenant_user_roles NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.tenant_user_roles DISABLE ROW LEVEL SECURITY;")
