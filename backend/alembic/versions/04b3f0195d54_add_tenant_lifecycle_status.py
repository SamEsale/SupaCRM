"""add_tenant_lifecycle_status

Revision ID: 04b3f0195d54
Revises: 6c2b5f9a8d13
Create Date: 2026-03-16 13:43:12.462803

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "04b3f0195d54"
down_revision = "6c2b5f9a8d13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
    )
    op.add_column(
        "tenants",
        sa.Column("status_reason", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "status_reason")
    op.drop_column("tenants", "status")