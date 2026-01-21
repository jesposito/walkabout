"""Oracle Review Models - SearchDefinition and ScrapeHealth

Oracle Review: Add models for proper price comparability and scrape health monitoring.

Revision ID: 002
Revises: 001
Create Date: 2026-01-21
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create SearchDefinition table
    op.create_table(
        'search_definitions',
        sa.Column('id', sa.Integer(), primary_key=True),
        
        # Route
        sa.Column('origin', sa.String(3), nullable=False),
        sa.Column('destination', sa.String(3), nullable=False),
        
        # Trip type
        sa.Column('trip_type', sa.Enum('round_trip', 'one_way', name='triptype'), default='round_trip', nullable=False),
        
        # Dates - flexible patterns
        sa.Column('departure_date_start', sa.Date(), nullable=True),  # Fixed mode
        sa.Column('departure_date_end', sa.Date(), nullable=True),
        sa.Column('departure_days_min', sa.Integer(), nullable=True),  # Rolling window mode
        sa.Column('departure_days_max', sa.Integer(), nullable=True),
        sa.Column('trip_duration_days_min', sa.Integer(), nullable=True),
        sa.Column('trip_duration_days_max', sa.Integer(), nullable=True),
        
        # Passengers
        sa.Column('adults', sa.Integer(), default=2, nullable=False),
        sa.Column('children', sa.Integer(), default=2, nullable=False),
        sa.Column('infants_in_seat', sa.Integer(), default=0, nullable=False),
        sa.Column('infants_on_lap', sa.Integer(), default=0, nullable=False),
        
        # Cabin and stops
        sa.Column('cabin_class', sa.Enum('economy', 'premium_economy', 'business', 'first', name='cabinclass'), default='economy', nullable=False),
        sa.Column('stops_filter', sa.Enum('any', 'nonstop', 'one_stop', 'two_plus', name='stopsfilter'), default='any', nullable=False),
        
        # Airline filters
        sa.Column('include_airlines', sa.String(100), nullable=True),
        sa.Column('exclude_airlines', sa.String(100), nullable=True),
        
        # Locale/currency
        sa.Column('currency', sa.String(3), default='NZD', nullable=False),
        sa.Column('locale', sa.String(10), default='en-NZ', nullable=False),
        
        # Bags
        sa.Column('carry_on_bags', sa.Integer(), default=0, nullable=False),
        sa.Column('checked_bags', sa.Integer(), default=0, nullable=False),
        
        # Metadata
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('scrape_frequency_hours', sa.Integer(), default=12, nullable=False),
        
        # Version tracking
        sa.Column('version', sa.Integer(), default=1, nullable=False),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    
    # Create indexes for SearchDefinition
    op.create_index('idx_search_definitions_origin_dest', 'search_definitions', ['origin', 'destination'])
    op.create_index('idx_search_definitions_active', 'search_definitions', ['is_active'])
    
    # Create ScrapeHealth table
    op.create_table(
        'scrape_health',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('search_definition_id', sa.Integer(), sa.ForeignKey('search_definitions.id', ondelete='CASCADE'), nullable=False, unique=True),
        
        # Success/failure tracking
        sa.Column('total_attempts', sa.Integer(), default=0, nullable=False),
        sa.Column('total_successes', sa.Integer(), default=0, nullable=False),
        sa.Column('total_failures', sa.Integer(), default=0, nullable=False),
        sa.Column('consecutive_failures', sa.Integer(), default=0, nullable=False),
        
        # Timestamps
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        
        # Failure details
        sa.Column('last_failure_reason', sa.String(50), nullable=True),
        sa.Column('last_failure_message', sa.Text(), nullable=True),
        sa.Column('last_screenshot_path', sa.String(500), nullable=True),
        sa.Column('last_html_snapshot_path', sa.String(500), nullable=True),
        
        # Stale data tracking
        sa.Column('stale_alert_sent_at', sa.DateTime(timezone=True), nullable=True),
        
        # Circuit breaker
        sa.Column('circuit_open', sa.Integer(), default=0, nullable=False),
        sa.Column('circuit_opened_at', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    
    # Create indexes for ScrapeHealth
    op.create_index('idx_scrape_health_search_def', 'scrape_health', ['search_definition_id'])
    
    # Update flight_prices table to use search_definition_id instead of route_id
    op.add_column('flight_prices', sa.Column('search_definition_id', sa.Integer(), sa.ForeignKey('search_definitions.id', ondelete='CASCADE'), nullable=True))
    
    # Make return_date nullable for one-way flights
    op.alter_column('flight_prices', 'return_date', nullable=True)
    
    # Remove duration_minutes and add it properly
    op.add_column('flight_prices', sa.Column('duration_minutes', sa.Integer(), nullable=True))
    
    # Create indexes for updated flight_prices
    op.create_index('idx_flight_prices_search_def_date', 'flight_prices', ['search_definition_id', 'departure_date'])
    
    # Note: We'll migrate data from route_id to search_definition_id in a future data migration
    # For now, both columns exist to allow gradual transition


def downgrade():
    # Drop indexes
    op.drop_index('idx_flight_prices_search_def_date')
    op.drop_index('idx_scrape_health_search_def')
    op.drop_index('idx_search_definitions_active')
    op.drop_index('idx_search_definitions_origin_dest')
    
    # Drop columns from flight_prices
    op.drop_column('flight_prices', 'duration_minutes')
    op.drop_column('flight_prices', 'search_definition_id')
    
    # Restore return_date as not nullable
    op.alter_column('flight_prices', 'return_date', nullable=False)
    
    # Drop tables
    op.drop_table('scrape_health')
    op.drop_table('search_definitions')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS triptype')
    op.execute('DROP TYPE IF EXISTS cabinclass') 
    op.execute('DROP TYPE IF EXISTS stopsfilter')