"""add payment gateway settings

Revision ID: 20260414_03
Revises: 20260414_02
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260414_03"
down_revision: Union[str, None] = "20260414_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "payment_gateway_settings",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "payment_gateway_settings")
