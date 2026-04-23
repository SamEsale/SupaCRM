"""add phone to marketing execution recipients

Revision ID: 20260422_01
Revises: 20260420_01
Create Date: 2026-04-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260422_01"
down_revision: Union[str, None] = "20260420_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketing_campaign_execution_recipients",
        sa.Column("phone", sa.String(length=50), nullable=True),
    )

    op.drop_constraint(
        "ck_marketing_campaign_executions_status_valid",
        "marketing_campaign_executions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_marketing_campaign_executions_status_valid",
        "marketing_campaign_executions",
        "status in ('queued', 'sending', 'completed', 'failed', 'blocked')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_marketing_campaign_executions_status_valid",
        "marketing_campaign_executions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_marketing_campaign_executions_status_valid",
        "marketing_campaign_executions",
        "status in ('sending', 'completed', 'failed', 'blocked')",
    )

    op.drop_column("marketing_campaign_execution_recipients", "phone")
