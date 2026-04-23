"""add marketing execution handoff traceability

Revision ID: 20260422_02
Revises: 20260422_01
Create Date: 2026-04-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260422_02"
down_revision: Union[str, None] = "20260422_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketing_campaign_execution_recipients",
        sa.Column("support_ticket_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "marketing_campaign_execution_recipients",
        sa.Column("handoff_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "marketing_campaign_execution_recipients",
        sa.Column("handoff_by_user_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "marketing_campaign_execution_recipients",
        sa.Column("handoff_status", sa.String(length=32), nullable=True),
    )
    op.create_foreign_key(
        "fk_marketing_execution_recipients_support_ticket_id",
        "marketing_campaign_execution_recipients",
        "support_tickets",
        ["support_ticket_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_marketing_execution_recipients_handoff_by_user_id",
        "marketing_campaign_execution_recipients",
        "users",
        ["handoff_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_marketing_campaign_execution_recipients_handoff_status_valid",
        "marketing_campaign_execution_recipients",
        "handoff_status is null or handoff_status in ('created', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_marketing_campaign_execution_recipients_handoff_status_valid",
        "marketing_campaign_execution_recipients",
        type_="check",
    )
    op.drop_constraint(
        "fk_marketing_execution_recipients_handoff_by_user_id",
        "marketing_campaign_execution_recipients",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_marketing_execution_recipients_support_ticket_id",
        "marketing_campaign_execution_recipients",
        type_="foreignkey",
    )
    op.drop_column("marketing_campaign_execution_recipients", "handoff_status")
    op.drop_column("marketing_campaign_execution_recipients", "handoff_by_user_id")
    op.drop_column("marketing_campaign_execution_recipients", "handoff_at")
    op.drop_column("marketing_campaign_execution_recipients", "support_ticket_id")
