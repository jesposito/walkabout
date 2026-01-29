"""Add notification preference columns to user_settings

Revision ID: 003_notification_preferences
Revises: 002_oracle_review_models
Create Date: 2026-01-30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add notification preference columns to user_settings
    op.add_column('user_settings', sa.Column('notification_provider', sa.String(20), nullable=True, server_default='none'))
    op.add_column('user_settings', sa.Column('notification_ntfy_url', sa.String(200), nullable=True))
    op.add_column('user_settings', sa.Column('notification_ntfy_topic', sa.String(100), nullable=True))
    op.add_column('user_settings', sa.Column('notification_discord_webhook', sa.String(300), nullable=True))
    op.add_column('user_settings', sa.Column('notification_quiet_hours_start', sa.Integer(), nullable=True))
    op.add_column('user_settings', sa.Column('notification_quiet_hours_end', sa.Integer(), nullable=True))
    op.add_column('user_settings', sa.Column('notification_cooldown_minutes', sa.Integer(), nullable=True, server_default='60'))
    op.add_column('user_settings', sa.Column('timezone', sa.String(50), nullable=True, server_default='Pacific/Auckland'))


def downgrade() -> None:
    op.drop_column('user_settings', 'timezone')
    op.drop_column('user_settings', 'notification_cooldown_minutes')
    op.drop_column('user_settings', 'notification_quiet_hours_end')
    op.drop_column('user_settings', 'notification_quiet_hours_start')
    op.drop_column('user_settings', 'notification_discord_webhook')
    op.drop_column('user_settings', 'notification_ntfy_topic')
    op.drop_column('user_settings', 'notification_ntfy_url')
    op.drop_column('user_settings', 'notification_provider')
