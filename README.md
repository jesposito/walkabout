# Walkabout

**Personal Flight Deal Intelligence Platform** - A self-hosted dashboard that aggregates flight deals, tracks prices, and monitors award availability for your specific routes.

```
Your flight intelligence, your data, your server.
```

## The Vision

Flight deal hunting is fragmented: deals are scattered across dozens of blogs, Google Flights lacks historical context, and award availability requires manual checking. For families planning 1-2 international trips per year, it's exhausting.

**Walkabout solves this with three pillars:**

| Pillar | Description |
|--------|-------------|
| **Deal Aggregator** | Unified feed from Secret Flying, OMAAT, TPG, etc., filtered to YOUR home airports |
| **Price Tracker** | Historical context for YOUR routes ("Is $800 AKL→LAX actually good?") |
| **Award Monitor** | Track points availability via Seats.aero (Phase 2) |

**Target User:** NZ-based families planning trips from AKL/CHC/WLG with school holiday constraints, comfortable self-hosting on Unraid/Docker.

## Why Not Just Use Google Flights Alerts?

Google is great for what it does. Walkabout fills the gaps:

- **Aggregated deal feeds** - One place for Secret Flying, OMAAT, TPG, etc.
- **Award flight tracking** - Points availability that Google doesn't show
- **Your historical context** - "Is this actually a good price for MY route?"
- **Self-hosted** - Your data stays on your server

## Current State (Phase 1a - "Prove Ingestion")

The app is a **single-container FastAPI monolith** focused on reliable data acquisition:

| Component | Status |
|-----------|--------|
| Deal RSS Aggregation | ✅ 12+ sources (Secret Flying, OMAAT, TPG, regional) |
| AI Deal Parsing | ✅ Optional Claude API enhancement |
| Google Flights Scraper | ✅ Playwright with stealth mode |
| Robust Price Analysis | ✅ Median/MAD z-scores + new low detection |
| Scrape Health & Circuit Breaker | ✅ Failure classification, auto-recovery |
| Trip Plans (Flexible Search) | ✅ Multi-origin/dest, budget constraints |
| ntfy Notifications | ✅ Deal alerts, system alerts |
| Server-rendered UI | ✅ Jinja2 templates with light/dark mode |
| Deal Scoring/Rating | ✅ Market price comparison |
| Discord Hall of Fame | ✅ Automated deal sharing |

**Tech Stack:** FastAPI + PostgreSQL + Playwright + APScheduler + ntfy

### What's Deferred (Phase 1b+)

- TimescaleDB (time-series optimization)
- Celery + Redis (distributed jobs)
- React SPA frontend
- Seats.aero award tracking
- Calendar heatmaps
- Multi-user support

### Architecture Philosophy

From Oracle Review feedback, deliberate choices were made:

- **Tighten MVP** around "reliable ingestion + alerts + minimal UI" before adding complexity
- **Rules detect, AI explains** - cheap math first, AI only when thresholds crossed
- **Single container** until complexity is needed
- **ScrapeHealth as first-class entity** - scraping is fragile, so track it properly

## Quick Start (Unraid)

1. **Install from Community Apps** (coming soon) or use docker-compose:

```bash
# Clone
git clone https://github.com/OWNER/walkabout.git
cd walkabout

# Configure
cp .env.example .env
# Edit .env with your settings

# Start
docker-compose -f docker-compose.phase1a.yml up -d
```

2. **Open the dashboard**: `http://your-server:8080`

3. **Set your profile**:
   - Home airport (e.g., AKL)
   - Destinations you care about
   - Notification preferences

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `TZ` | Your timezone | `Pacific/Auckland` |
| `NTFY_URL` | ntfy server URL for alerts | `http://localhost:8080` |
| `NTFY_TOPIC` | ntfy topic name | `walkabout-deals` |
| `ANTHROPIC_API_KEY` | For AI deal parsing (optional) | - |
| `DEAL_THRESHOLD_Z_SCORE` | Alert threshold (robust z-score) | `-1.5` |
| `SEATS_AERO_API_KEY` | For award monitoring (Phase 2) | - |

## Architecture

Single container, simple stack:

```
┌─────────────────────────────────────────────────────────────┐
│              Walkabout Phase 1a Stack                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FastAPI Backend (Python)                                   │
│  ├─ Route Handlers (deals, status, health, notifications)  │
│  ├─ Scraping Service (Google Flights via Playwright)       │
│  ├─ Price Analyzer (robust z-score + new lows)             │
│  ├─ Deal Feed Aggregator (RSS parsing)                     │
│  ├─ APScheduler (background jobs)                          │
│  └─ Notification Service (ntfy integration)                │
│                                                             │
│  Database: PostgreSQL + SQLAlchemy ORM                      │
│  Files: Screenshots & HTML snapshots for debugging          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Data Sources

### Deal Feeds (RSS)
- Secret Flying - `secretflying.com/feed/`
- One Mile at a Time - deals RSS
- The Points Guy - deals section
- Australian Frequent Flyer - covers NZ routes
- Holiday Pirates, Ozbargain, Cheapies NZ (regional)

### Price Data
- Google Flights (via Playwright scraper)
- Amadeus API (free tier)
- SerpAPI fallback

### Award Availability (Phase 2)
- **Seats.aero** ($10/mo Pro subscription)
- Tracks: United, Aeroplan, Qantas FF, Velocity

## Documentation

- [Vision & Product](docs/VISION.md) - Product vision and positioning
- [Architecture](docs/ARCHITECTURE.md) - Data model and technical design
- [UX Design](docs/UX_DESIGN.md) - User flows and interface design
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Phased build approach
- [Oracle Review](docs/ORACLE_REVIEW.md) - Critical feedback and responses

## Development

```bash
# Run with docker-compose
docker-compose -f docker-compose.phase1a.yml up -d

# Run tests
docker-compose exec backend pytest

# View logs
docker-compose logs -f backend
```

## Unraid Installation

See [UNRAID_DEPLOYMENT.md](UNRAID_DEPLOYMENT.md) for detailed Unraid setup instructions.

## License

MIT
