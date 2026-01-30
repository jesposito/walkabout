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

## Current State (Phase 1a)

The app is a **single-container FastAPI monolith** with SQLite:

| Component | Status |
|-----------|--------|
| Deal RSS Aggregation | RSS sources (Secret Flying, OMAAT, TPG, regional) |
| AI Deal Parsing | Optional Claude/Ollama API enhancement |
| Google Flights Scraper | Playwright with stealth mode |
| Robust Price Analysis | Median/MAD z-scores + new low detection |
| Scrape Health & Circuit Breaker | Failure classification, auto-recovery |
| Trip Plans (Flexible Search) | Multi-origin/dest, budget constraints |
| Notifications | ntfy and Discord webhook support |
| Server-rendered UI | Jinja2 templates with light/dark mode |
| Deal Scoring/Rating | Market price comparison |
| Settings UI | Full configuration via web interface |

**Tech Stack:** FastAPI + SQLite + Playwright + APScheduler

### What's Deferred (Phase 1b+)

- TimescaleDB (time-series optimization)
- Celery + Redis (distributed jobs)
- React SPA frontend
- Seats.aero award tracking
- Calendar heatmaps
- Multi-user support

## Quick Start (Docker)

### Single Container Deployment

```bash
# Create data directory
mkdir -p /path/to/walkabout/data

# Run the container
docker run -d \
  --name walkabout \
  -p 8000:8000 \
  -v /path/to/walkabout/data:/app/data \
  -e TZ=Pacific/Auckland \
  --restart unless-stopped \
  ghcr.io/jesposito/walkabout:latest
```

### Open the Dashboard

1. Visit `http://your-server:8000`
2. Go to **Settings** to configure:
   - Home airports (e.g., AKL, WLG, CHC)
   - AI provider (optional - Claude or Ollama)
   - Notification provider (ntfy or Discord)
   - Notification preferences

### Unraid

See [UNRAID_DEPLOYMENT.md](UNRAID_DEPLOYMENT.md) for detailed Unraid setup instructions.

## Configuration

All configuration is done via the **Settings** page in the web UI:

| Setting | Description |
|---------|-------------|
| Home Airports | Your departure airports for deal filtering |
| AI Provider | Optional - Claude API or local Ollama for deal parsing |
| Notification Provider | ntfy server or Discord webhook |
| Notification Preferences | Quiet hours, cooldowns, minimum deal rating |
| Timezone | For scheduling and quiet hours |

### Environment Variables

Only a few environment variables are needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Your timezone | `Pacific/Auckland` |
| `DATABASE_URL` | SQLite path (optional override) | `sqlite:///./data/walkabout.db` |

## Architecture

Single container, simple stack:

```
┌─────────────────────────────────────────────────────────────┐
│              Walkabout Phase 1a Stack                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FastAPI Backend (Python)                                   │
│  ├─ Route Handlers (deals, trips, settings, health)        │
│  ├─ Scraping Service (Google Flights via Playwright)       │
│  ├─ Price Analyzer (robust z-score + new lows)             │
│  ├─ Deal Feed Aggregator (RSS parsing)                     │
│  ├─ APScheduler (background jobs)                          │
│  └─ Notification Service (ntfy/Discord integration)        │
│                                                             │
│  Database: SQLite + SQLAlchemy ORM                          │
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
- Fly4Free, regional sources

### Price Data
- Google Flights (via Playwright scraper)

### Award Availability (Phase 2)
- **Seats.aero** ($10/mo Pro subscription)
- Tracks: United, Aeroplan, Qantas FF, Velocity

## Documentation

- [Unraid Deployment](UNRAID_DEPLOYMENT.md) - Unraid-specific setup instructions
- [Phase 1a Details](PHASE1A_README.md) - Phase 1a implementation details
- [Changelog](CHANGELOG.md) - Version history

## Development

```bash
# Clone the repo
git clone https://github.com/jesposito/walkabout.git
cd walkabout

# Run locally with Docker
docker build -t walkabout .
docker run -p 8000:8000 -v ./data:/app/data walkabout

# Or run directly (requires Python 3.11+)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Community

- **Discord**: [Join the community](https://discord.gg/eKg4MhMkVJ)
- **Support**: [Buy Me a Coffee](https://buymeacoffee.com/jesposito)
- **Issues**: [GitHub Issues](https://github.com/jesposito/walkabout/issues)

## License

MIT
