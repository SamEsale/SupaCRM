"""align deal stage and status constraints with sales contract

Revision ID: 20260412_02
Revises: 20260412_01
Create Date: 2026-04-12
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260412_02"
down_revision: Union[str, None] = "20260412_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        update public.deals
        set stage = case lower(stage)
            when 'lead' then 'new lead'
            when 'qualified' then 'qualified lead'
            when 'proposal' then 'proposal sent'
            when 'estimate' then 'estimate sent'
            when 'negotiation' then 'negotiating contract terms'
            when 'contracted' then 'contract signed'
            when 'won' then 'contract signed'
            when 'lost' then 'deal not secured'
            else stage
        end
        """
    )

    op.execute(
        """
        ALTER TABLE public.deals
        DROP CONSTRAINT IF EXISTS ck_deals_stage_valid
        """
    )

    op.execute(
        """
        ALTER TABLE public.deals
        ADD CONSTRAINT ck_deals_stage_valid
        CHECK (
            stage in (
                'new lead',
                'qualified lead',
                'proposal sent',
                'estimate sent',
                'negotiating contract terms',
                'contract signed',
                'deal not secured'
            )
        )
        """
    )

    op.execute(
        """
        ALTER TABLE public.deals
        DROP CONSTRAINT IF EXISTS ck_deals_status_valid
        """
    )

    op.execute(
        """
        ALTER TABLE public.deals
        ADD CONSTRAINT ck_deals_status_valid
        CHECK (
            status in (
                'open',
                'in progress',
                'won',
                'lost'
            )
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.deals
        DROP CONSTRAINT IF EXISTS ck_deals_status_valid
        """
    )

    op.execute(
        """
        ALTER TABLE public.deals
        ADD CONSTRAINT ck_deals_status_valid
        CHECK (
            status in (
                'open',
                'in progress',
                'won',
                'lost',
                'archived'
            )
        )
        """
    )

    op.execute(
        """
        ALTER TABLE public.deals
        DROP CONSTRAINT IF EXISTS ck_deals_stage_valid
        """
    )

    op.execute(
        """
        ALTER TABLE public.deals
        ADD CONSTRAINT ck_deals_stage_valid
        CHECK (
            stage in (
                'lead',
                'new lead',
                'qualified',
                'proposal',
                'estimate',
                'negotiation',
                'contracted',
                'won',
                'lost'
            )
        )
        """
    )
