"""add_commercial_payment_methods_table

Revision ID: 20260422_04
Revises: 20260422_03
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260422_04"
down_revision: Union[str, None] = "20260422_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


POLICY_NAME = "commercial_payment_methods_tenant_isolation"


def upgrade() -> None:
    op.create_table(
        'commercial_payment_methods',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(64), nullable=False),
        sa.Column('provider_customer_id', sa.String(128), nullable=False),
        sa.Column('provider_payment_method_id', sa.String(128), nullable=False),
        sa.Column('provider_type', sa.String(32), nullable=False, server_default='stripe'),
        sa.Column('card_brand', sa.String(32), nullable=True),
        sa.Column('card_last4', sa.String(4), nullable=True),
        sa.Column('card_exp_month', sa.Integer, nullable=True),
        sa.Column('card_exp_year', sa.Integer, nullable=True),
        sa.Column('billing_email', sa.String(255), nullable=True),
        sa.Column('billing_name', sa.String(255), nullable=True),
        sa.Column('is_default', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_commercial_payment_methods_tenant_id', 'commercial_payment_methods', ['tenant_id'])
    op.create_index('ix_commercial_payment_methods_provider_customer_id', 'commercial_payment_methods', ['provider_customer_id'])
    op.create_index('ix_commercial_payment_methods_provider_payment_method_id', 'commercial_payment_methods', ['provider_payment_method_id'], unique=True)
    op.execute("ALTER TABLE public.commercial_payment_methods ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.commercial_payment_methods FORCE ROW LEVEL SECURITY;")
    op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON public.commercial_payment_methods;")
    op.execute(
        f"""
        CREATE POLICY {POLICY_NAME}
        ON public.commercial_payment_methods
        USING ((tenant_id)::text = current_setting('app.tenant_id'::text, true))
        WITH CHECK ((tenant_id)::text = current_setting('app.tenant_id'::text, true));
        """
    )


def downgrade() -> None:
    op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON public.commercial_payment_methods;")
    op.execute("ALTER TABLE public.commercial_payment_methods NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE public.commercial_payment_methods DISABLE ROW LEVEL SECURITY;")
    op.drop_index('ix_commercial_payment_methods_provider_payment_method_id', table_name='commercial_payment_methods')
    op.drop_index('ix_commercial_payment_methods_provider_customer_id', table_name='commercial_payment_methods')
    op.drop_index('ix_commercial_payment_methods_tenant_id', table_name='commercial_payment_methods')
    op.drop_table('commercial_payment_methods')
