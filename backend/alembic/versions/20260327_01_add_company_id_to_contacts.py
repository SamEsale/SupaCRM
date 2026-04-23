"""add company_id to contacts

Revision ID: 20260327_01
Revises: 20260325_01
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa


revision = "20260327_01"
down_revision = "9009424468f8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contacts",
        sa.Column("company_id", sa.String(length=36), nullable=True),
        schema="public",
    )

    op.execute(
        """
        update public.contacts c
        set company_id = co.id
        from public.companies co
        where c.tenant_id = co.tenant_id
          and c.company is not null
          and btrim(c.company) <> ''
          and lower(btrim(c.company)) = lower(btrim(co.name))
        """
    )

    op.create_foreign_key(
        "fk_contacts_company_id_companies",
        "contacts",
        "companies",
        ["company_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_contacts_tenant_company_id",
        "contacts",
        ["tenant_id", "company_id"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contacts_tenant_company_id",
        table_name="contacts",
        schema="public",
    )

    op.drop_constraint(
        "fk_contacts_company_id_companies",
        "contacts",
        schema="public",
        type_="foreignkey",
    )

    op.drop_column("contacts", "company_id", schema="public")
