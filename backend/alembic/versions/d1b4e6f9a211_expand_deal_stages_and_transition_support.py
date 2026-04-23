"""expand deal stages and transition support

Revision ID: d1b4e6f9a211
Revises: c9a8e7b4d521
Create Date: 2026-03-24 13:05:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "d1b4e6f9a211"
down_revision = "c9a8e7b4d521"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
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
                'qualified',
                'proposal',
                'estimate',
                'negotiation',
                'won',
                'lost'
            )
        )
        """
    )