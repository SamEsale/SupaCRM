"""enable RLS for mounted tenant business tables

Revision ID: 20260405_01
Revises: 20260402_02
Create Date: 2026-04-05
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260405_01"
down_revision: Union[str, None] = "20260402_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TARGET_TABLES: tuple[str, ...] = (
    "companies",
    "contacts",
    "deals",
    "quotes",
    "invoices",
)


def _policy_name(table: str) -> str:
    return f"{table}_tenant_isolation"


def upgrade() -> None:
    for table in TARGET_TABLES:
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
    for table in TARGET_TABLES:
        policy_name = _policy_name(table)
        op.execute(f"DROP POLICY IF EXISTS {policy_name} ON public.{table};")
        op.execute(f"ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
