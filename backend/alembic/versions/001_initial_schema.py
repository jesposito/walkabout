"""Initial schema

Revision ID: 001
Create Date: 2026-01-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'routes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('origin', sa.String(3), nullable=False),
        sa.Column('destination', sa.String(3), nullable=False),
        sa.Column('name', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('scrape_frequency_hours', sa.Integer(), default=12),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    
    op.create_table(
        'flight_prices',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('route_id', sa.Integer(), sa.ForeignKey('routes.id'), nullable=False),
        sa.Column('scraped_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('departure_date', sa.Date(), nullable=False),
        sa.Column('return_date', sa.Date(), nullable=False),
        sa.Column('price_nzd', sa.Numeric(10, 2), nullable=False),
        sa.Column('airline', sa.String(100)),
        sa.Column('stops', sa.Integer(), default=0),
        sa.Column('cabin_class', sa.String(20), default='economy'),
        sa.Column('passengers', sa.Integer(), default=4),
        sa.Column('raw_data', postgresql.JSONB()),
    )
    
    op.create_table(
        'alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('route_id', sa.Integer(), sa.ForeignKey('routes.id'), nullable=False),
        sa.Column('flight_price_id', sa.BigInteger(), sa.ForeignKey('flight_prices.id')),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('price_nzd', sa.Numeric(10, 2)),
        sa.Column('z_score', sa.Numeric(5, 2)),
        sa.Column('message', sa.Text()),
        sa.Column('ai_analysis', sa.Text()),
    )
    
    op.create_index('idx_flight_prices_route_date', 'flight_prices', ['route_id', 'departure_date'])
    op.create_index('idx_flight_prices_scraped', 'flight_prices', ['scraped_at'])
    
    op.execute("SELECT create_hypertable('flight_prices', 'scraped_at', chunk_time_interval => INTERVAL '1 week', if_not_exists => TRUE)")


def downgrade():
    op.drop_table('alerts')
    op.drop_table('flight_prices')
    op.drop_table('routes')
