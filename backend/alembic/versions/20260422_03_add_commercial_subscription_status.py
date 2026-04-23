"""add commercial subscription status

Revision ID: 20260422_03
Revises: 20260422_02
Create Date: 2026-04-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260422_03"
down_revision: Union[str, None] = "20260422_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commercial_subscriptions",
        sa.Column("subscription_status", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("commercial_subscriptions", "subscription_status")
