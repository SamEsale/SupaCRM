"""add tenant branding and integration settings

Revision ID: 20260406_02
Revises: 20260406_01
Create Date: 2026-04-06 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260406_02"
down_revision = "20260406_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("logo_file_key", sa.String(length=512), nullable=True))
    op.add_column(
        "tenants",
        sa.Column(
            "whatsapp_settings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "smtp_settings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "smtp_settings")
    op.drop_column("tenants", "whatsapp_settings")
    op.drop_column("tenants", "logo_file_key")
