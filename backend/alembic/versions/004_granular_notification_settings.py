"""Add granular notification settings columns to user_settings

Revision ID: 004_granular_notification_settings
Revises: 003_notification_preferences
Create Date: 2026-01-30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Granular notification toggles
    op.add_column('user_settings', sa.Column('notify_deals', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('user_settings', sa.Column('notify_trip_matches', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('user_settings', sa.Column('notify_route_updates', sa.Boolean(), nullable=True, server_default='1'))
    op.add_column('user_settings', sa.Column('notify_system', sa.Boolean(), nullable=True, server_default='1'))

    # Deal notification filters
    op.add_column('user_settings', sa.Column('deal_notify_min_rating', sa.Integer(), nullable=True, server_default='3'))
    op.add_column('user_settings', sa.Column('deal_notify_categories', sa.JSON(), nullable=True))
    op.add_column('user_settings', sa.Column('deal_notify_cabin_classes', sa.JSON(), nullable=True))

    # Frequency controls
    op.add_column('user_settings', sa.Column('deal_cooldown_minutes', sa.Integer(), nullable=True, server_default='60'))
    op.add_column('user_settings', sa.Column('trip_cooldown_hours', sa.Integer(), nullable=True, server_default='6'))
    op.add_column('user_settings', sa.Column('route_cooldown_hours', sa.Integer(), nullable=True, server_default='24'))

    # Daily digest
    op.add_column('user_settings', sa.Column('daily_digest_enabled', sa.Boolean(), nullable=True, server_default='0'))
    op.add_column('user_settings', sa.Column('daily_digest_hour', sa.Integer(), nullable=True, server_default='8'))


def downgrade() -> None:
    op.drop_column('user_settings', 'daily_digest_hour')
    op.drop_column('user_settings', 'daily_digest_enabled')
    op.drop_column('user_settings', 'route_cooldown_hours')
    op.drop_column('user_settings', 'trip_cooldown_hours')
    op.drop_column('user_settings', 'deal_cooldown_minutes')
    op.drop_column('user_settings', 'deal_notify_cabin_classes')
    op.drop_column('user_settings', 'deal_notify_categories')
    op.drop_column('user_settings', 'deal_notify_min_rating')
    op.drop_column('user_settings', 'notify_system')
    op.drop_column('user_settings', 'notify_route_updates')
    op.drop_column('user_settings', 'notify_trip_matches')
    op.drop_column('user_settings', 'notify_deals')
