"""add deal follow-up and reporting fields

Revision ID: 20260412_01
Revises: 20260406_02
Create Date: 2026-04-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260412_01"
down_revision: Union[str, None] = "20260406_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("deals", sa.Column("follow_up_note", sa.Text(), nullable=True))
    op.add_column("deals", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        update public.deals
        set closed_at = updated_at
        where status in ('won', 'lost')
          and closed_at is null
        """
    )


def downgrade() -> None:
    op.drop_column("deals", "closed_at")
    op.drop_column("deals", "follow_up_note")
    op.drop_column("deals", "next_follow_up_at")
