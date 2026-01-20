# Walkabout

Self-hosted travel deal monitor for tracking flight prices, award availability, and resort deals.

## Features

- **Multi-destination monitoring** - Track flights from any origin to any destination
- **Cash fare tracking** - Automated Google Flights scraping (2x daily)
- **Award flight availability** - Seats.aero integration for miles redemptions
- **AI-powered analysis** - Claude explains deals and provides booking advice
- **Smart alerts** - ntfy notifications when prices drop
- **Historical analysis** - Z-score based deal detection

## Quick Start

```bash
# Clone and configure
git clone <repo-url> walkabout
cd walkabout
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Run database migrations
docker-compose exec backend alembic upgrade head

# Add your first route
curl -X POST http://localhost:8000/api/routes \
  -H "Content-Type: application/json" \
  -d '{"origin": "AKL", "destination": "HNL", "name": "Auckland to Honolulu"}'

# Access the dashboard
open http://localhost:3000
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | React dashboard |
| Backend | 8000 | FastAPI + Swagger docs |
| ntfy | 8080 | Notification server |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend  │  Backend   │  Celery    │  Celery  │  ntfy    │
│  (React)   │  (FastAPI) │  Worker    │  Beat    │          │
├─────────────────────────────────────────────────────────────┤
│            PostgreSQL + TimescaleDB  │  Redis              │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

Create `.env` from `.env.example`:

```env
DB_PASSWORD=your_secure_password
SEATS_AERO_API_KEY=your_key        # For award availability (optional)
ANTHROPIC_API_KEY=your_key         # For AI analysis (optional)
NTFY_TOPIC=walkabout-deals
```

## Documentation

- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Detailed development roadmap
- [Architecture](docs/ARCHITECTURE.md) - Technical design decisions
- [Decisions](docs/DECISIONS.md) - Project decisions and rationale
- [Research](docs/RESEARCH.md) - API and scraping research

## License

MIT
