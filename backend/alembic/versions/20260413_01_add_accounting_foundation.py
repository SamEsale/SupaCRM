"""add accounting foundation

Revision ID: 20260413_01
Revises: 20260412_04
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260413_01"
down_revision: Union[str, None] = "20260412_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounting_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("system_key", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_accounting_accounts_tenant_code"),
        sa.CheckConstraint(
            "account_type in ('asset', 'liability', 'equity', 'revenue', 'expense')",
            name="ck_accounting_accounts_type_valid",
        ),
    )
    op.create_index("ix_accounting_accounts_tenant_id", "accounting_accounts", ["tenant_id"], unique=False)
    op.create_index("ix_accounting_accounts_system_key", "accounting_accounts", ["system_key"], unique=False)

    op.create_table(
        "journal_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("memo", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("source_event", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "source_type",
            "source_id",
            "source_event",
            name="uq_journal_entries_tenant_source_event",
        ),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_journal_entries_currency_length"),
    )
    op.create_index("ix_journal_entries_tenant_id", "journal_entries", ["tenant_id"], unique=False)
    op.create_index(
        "ix_journal_entries_source_lookup",
        "journal_entries",
        ["tenant_id", "source_type", "source_id", "source_event"],
        unique=False,
    )

    op.create_table(
        "journal_entry_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("journal_entry_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("line_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("debit_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("credit_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounting_accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "((debit_amount > 0 and credit_amount = 0) or (credit_amount > 0 and debit_amount = 0))",
            name="ck_journal_entry_lines_one_sided_amount",
        ),
    )
    op.create_index("ix_journal_entry_lines_tenant_id", "journal_entry_lines", ["tenant_id"], unique=False)
    op.create_index(
        "ix_journal_entry_lines_journal_entry_id",
        "journal_entry_lines",
        ["journal_entry_id"],
        unique=False,
    )

    op.execute("ALTER TABLE public.accounting_accounts ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.accounting_accounts FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS accounting_accounts_tenant_isolation ON public.accounting_accounts;")
    op.execute(
        """
        CREATE POLICY accounting_accounts_tenant_isolation
        ON public.accounting_accounts
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )

    op.execute("ALTER TABLE public.journal_entries ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.journal_entries FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS journal_entries_tenant_isolation ON public.journal_entries;")
    op.execute(
        """
        CREATE POLICY journal_entries_tenant_isolation
        ON public.journal_entries
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )

    op.execute("ALTER TABLE public.journal_entry_lines ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.journal_entry_lines FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS journal_entry_lines_tenant_isolation ON public.journal_entry_lines;")
    op.execute(
        """
        CREATE POLICY journal_entry_lines_tenant_isolation
        ON public.journal_entry_lines
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS journal_entry_lines_tenant_isolation ON public.journal_entry_lines;")
    op.execute("ALTER TABLE public.journal_entry_lines NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.journal_entry_lines DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS journal_entries_tenant_isolation ON public.journal_entries;")
    op.execute("ALTER TABLE public.journal_entries NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.journal_entries DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS accounting_accounts_tenant_isolation ON public.accounting_accounts;")
    op.execute("ALTER TABLE public.accounting_accounts NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.accounting_accounts DISABLE ROW LEVEL SECURITY;")
    op.drop_index("ix_journal_entry_lines_journal_entry_id", table_name="journal_entry_lines")
    op.drop_index("ix_journal_entry_lines_tenant_id", table_name="journal_entry_lines")
    op.drop_table("journal_entry_lines")
    op.drop_index("ix_journal_entries_source_lookup", table_name="journal_entries")
    op.drop_index("ix_journal_entries_tenant_id", table_name="journal_entries")
    op.drop_table("journal_entries")
    op.drop_index("ix_accounting_accounts_system_key", table_name="accounting_accounts")
    op.drop_index("ix_accounting_accounts_tenant_id", table_name="accounting_accounts")
    op.drop_table("accounting_accounts")
