#!/bin/bash
# Phase 1a startup script - minimal system to prove scraping works

set -e

echo "🚀 Starting Walkabout Phase 1a (Prove Ingestion)"
echo "════════════════════════════════════════════════"

# Create data directories
echo "📁 Creating data directories..."
mkdir -p ./data/screenshots
mkdir -p ./data/html_snapshots

# Ensure environment file exists
if [ ! -f .env ]; then
    echo "📄 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your settings, then re-run this script"
    exit 1
fi

# Stop any running containers
echo "🛑 Stopping any existing containers..."
docker-compose -f docker-compose.phase1a.yml down --remove-orphans

# Start Phase 1a services
echo "🐳 Starting Phase 1a services..."
docker-compose -f docker-compose.phase1a.yml up -d

# Wait for database
echo "⏳ Waiting for database to be ready..."
until docker-compose -f docker-compose.phase1a.yml exec -T db pg_isready -U walkabout; do
  echo "   Database not ready yet, waiting..."
  sleep 2
done

# Run migrations
echo "🗄️  Running database migrations..."
docker-compose -f docker-compose.phase1a.yml exec backend alembic upgrade head

# Create sample search definition if none exist
echo "🔍 Setting up sample search definition..."
docker-compose -f docker-compose.phase1a.yml exec -T backend python -c "
import sys
sys.path.append('/app')

from app.database import SessionLocal, engine
from app.models import SearchDefinition, TripType, CabinClass, StopsFilter
from sqlalchemy import text

# Create tables if they don't exist
from app.database import Base
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Check if we already have search definitions
existing_count = db.execute(text('SELECT COUNT(*) FROM search_definitions')).scalar()

if existing_count == 0:
    print('Creating sample AKL→HNL search definition...')
    search_def = SearchDefinition(
        origin='AKL',
        destination='HNL', 
        name='Auckland to Honolulu (Family)',
        trip_type=TripType.ROUND_TRIP,
        adults=2,
        children=2,
        cabin_class=CabinClass.ECONOMY,
        stops_filter=StopsFilter.ANY,
        departure_days_min=60,
        departure_days_max=90,
        trip_duration_days_min=7,
        trip_duration_days_max=14,
        currency='NZD',
        locale='en-NZ',
        is_active=True,
        scrape_frequency_hours=12
    )
    db.add(search_def)
    db.commit()
    print(f'Created search definition: {search_def.display_name}')
else:
    print(f'Found {existing_count} existing search definitions')

db.close()
"

echo "✅ Phase 1a setup complete!"
echo ""
echo "🔗 Access points:"
echo "   📊 Status Page:     http://localhost:8000/"
echo "   📡 API Docs:        http://localhost:8000/docs" 
echo "   🔔 ntfy:           http://localhost:8080/"
echo ""
echo "📋 Next steps:"
echo "   1. Visit http://localhost:8000/ to see status"
echo "   2. Trigger a manual scrape to test"
echo "   3. Check ntfy for notifications"
echo "   4. Monitor for 7 days to validate <10% failure rate"
echo ""
echo "🐳 View logs:"
echo "   docker-compose -f docker-compose.phase1a.yml logs -f backend"