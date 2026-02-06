"""Add confidence and is_suspicious columns to flight_prices

Revision ID: 005
Revises: 004
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('flight_prices', sa.Column('confidence', sa.Numeric(5, 4), nullable=True))
    op.add_column('flight_prices', sa.Column('is_suspicious', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('flight_prices', 'is_suspicious')
    op.drop_column('flight_prices', 'confidence')
