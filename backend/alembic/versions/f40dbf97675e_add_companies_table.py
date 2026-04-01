"""add_companies_table

Revision ID: f40dbf97675e
Revises: 2b82f1d6224c
Create Date: 2026-03-16 15:54:55.608173

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f40dbf97675e"
down_revision = "2b82f1d6224c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_companies_tenant_name"),
    )
    op.create_index(op.f("ix_companies_tenant_id"), "companies", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_companies_tenant_id"), table_name="companies")
    op.drop_table("companies")