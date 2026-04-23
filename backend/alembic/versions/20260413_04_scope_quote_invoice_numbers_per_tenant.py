"""scope quote and invoice numbers per tenant

Revision ID: 20260413_04
Revises: 20260413_03
Create Date: 2026-04-13
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260413_04"
down_revision: Union[str, None] = "20260413_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_quotes_number", "quotes", type_="unique")
    op.create_unique_constraint("uq_quotes_tenant_number", "quotes", ["tenant_id", "number"])

    op.drop_constraint("uq_invoices_number", "invoices", type_="unique")
    op.create_unique_constraint("uq_invoices_tenant_number", "invoices", ["tenant_id", "number"])


def downgrade() -> None:
    op.drop_constraint("uq_quotes_tenant_number", "quotes", type_="unique")
    op.create_unique_constraint("uq_quotes_number", "quotes", ["number"])

    op.drop_constraint("uq_invoices_tenant_number", "invoices", type_="unique")
    op.create_unique_constraint("uq_invoices_number", "invoices", ["number"])
