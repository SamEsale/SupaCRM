"""add company address vat and registration fields

Revision ID: 9009424468f8
Revises: d1b4e6f9a211
Create Date: 2026-03-25 15:36:42.712871

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9009424468f8"
down_revision = "d1b4e6f9a211"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("companies", sa.Column("vat_number", sa.String(length=64), nullable=True))
    op.add_column("companies", sa.Column("registration_number", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "registration_number")
    op.drop_column("companies", "vat_number")
    op.drop_column("companies", "address")