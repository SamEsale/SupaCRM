"""add_contacts_table

Revision ID: 2b82f1d6224c
Revises: 04b3f0195d54
Create Date: 2026-03-16 14:33:49.498169

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b82f1d6224c"
down_revision = "04b3f0195d54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("job_title", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_contacts_tenant_email"),
    )
    op.create_index(op.f("ix_contacts_tenant_id"), "contacts", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_contacts_tenant_id"), table_name="contacts")
    op.drop_table("contacts")