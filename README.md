# Walkabout

**Personal Flight Deal Intelligence Platform** - A self-hosted dashboard that aggregates flight deals, tracks prices, monitors award availability, and provides AI-powered insights for your specific routes.

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
| **Award Monitor** | Track points availability via Seats.aero across United, Aeroplan, Qantas, and more |

**Target User:** Families planning 1-2 international trips per year, comfortable self-hosting on Unraid/Docker.

## Why Not Just Use Google Flights Alerts?

Google is great for what it does. Walkabout fills the gaps:

- **Aggregated deal feeds** - One place for Secret Flying, OMAAT, TPG, etc.
- **Award flight tracking** - Points availability that Google doesn't show
- **Your historical context** - "Is this actually a good price for MY route?"
- **AI intelligence** - Deal explanations, trip feasibility, award sweet spots
- **Self-hosted** - Your data stays on your server

## Current State

The app is a **single-container FastAPI + React monolith** with SQLite:

| Component | Status |
|-----------|--------|
| React SPA Frontend | Dark/light mode, mobile-responsive with bottom nav |
| Deal RSS Aggregation | 15+ RSS sources (Secret Flying, OMAAT, TPG, regional) |
| AI Deal Intelligence | Claude/Ollama-powered deal explanations, settings review, trip planning |
| Google Flights Scraper | Playwright with stealth mode and confidence gating |
| SerpAPI Integration | Google Flights data with price insights and deep search |
| Amadeus Integration | GDS flight data with price analysis metrics |
| Trip Plans | Multi-origin/destination flexible search with AI feasibility checks |
| Award Tracking | Seats.aero integration with AI pattern analysis and mile valuation |
| Notifications | ntfy and Discord webhook support with granular controls |
| Robust Price Analysis | Median/MAD z-scores + new low detection |
| Scrape Health | Failure classification, circuit breaker, auto-recovery |

**Tech Stack:** FastAPI + React + SQLite + Playwright + APScheduler

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
  -e TZ=America/New_York \
  --restart unless-stopped \
  ghcr.io/jesposito/walkabout:latest
```

### Open the Dashboard

1. Visit `http://your-server:8000`
2. Go to **Settings** to configure:
   - Home airports (e.g., LAX, JFK, ORD)
   - AI provider (optional - Claude or Ollama)
   - API keys (SerpAPI, Amadeus, Seats.aero - all optional)
   - Notification provider (ntfy or Discord)
   - Notification preferences

### Unraid

See [UNRAID_DEPLOYMENT.md](UNRAID_DEPLOYMENT.md) for detailed Unraid setup instructions.

## Configuration

All configuration is done via the **Settings** page in the web UI:

| Setting | Description |
|---------|-------------|
| Home Airports | Your departure airports for deal filtering |
| AI Provider | Optional - Claude API or local Ollama for deal intelligence |
| SerpAPI Key | Optional - Google Flights price data with insights |
| Amadeus Credentials | Optional - GDS flight data and price analysis |
| Seats.aero Key | Optional - Award availability tracking ($10/mo Pro) |
| Notification Provider | ntfy server or Discord webhook |
| Notification Preferences | Quiet hours, cooldowns, minimum deal rating, category filters |
| Timezone | For scheduling and quiet hours |

### Environment Variables

Only a few environment variables are needed:

| Variable | Description | Default |
|----------|-------------|---------|
| `TZ` | Your timezone | `America/New_York` |
| `DATABASE_URL` | SQLite path (optional override) | `sqlite:///./data/walkabout.db` |

## Architecture

Single container, multi-source stack:

```
┌─────────────────────────────────────────────────────────────┐
│              Walkabout Stack                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  React SPA (Vite + TailwindCSS + React Router)              │
│  ├─ Dashboard (status, deals, AI digest)                    │
│  ├─ Deals (categorized feed with AI explanations)           │
│  ├─ Trips (multi-leg planner with AI feasibility)           │
│  ├─ Awards (Seats.aero tracking with AI analysis)           │
│  └─ Settings (full config with AI review)                   │
│                                                              │
│  FastAPI Backend (Python)                                    │
│  ├─ Route Handlers (deals, trips, settings, awards, ai)     │
│  ├─ Price Sources (SerpAPI, Amadeus, Playwright scraper)    │
│  ├─ AI Service Layer (Claude/Ollama with cost tracking)     │
│  ├─ Deal Feed Aggregator (RSS parsing + AI enhancement)     │
│  ├─ APScheduler (background jobs)                           │
│  └─ Notification Service (ntfy/Discord)                     │
│                                                              │
│  Database: SQLite + SQLAlchemy ORM                           │
│  Files: Screenshots & HTML snapshots for debugging           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Data Sources

### Deal Feeds (RSS)
- Secret Flying - `secretflying.com/feed/`
- One Mile at a Time - deals RSS
- The Points Guy - deals section
- Australian Frequent Flyer - Asia-Pacific routes
- Fly4Free, regional sources

### Price Data
- **SerpAPI** - Google Flights data with price insights (recommended)
- **Amadeus** - GDS flight data with price analysis metrics
- **Google Flights Scraper** - Playwright-based fallback with confidence gating

### Award Availability
- **Seats.aero** ($10/mo Pro subscription)
- Tracks: United, Aeroplan, Qantas FF, Velocity, and more

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

# Or run backend directly (requires Python 3.11+)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend development (requires Node.js 18+)
cd frontend
npm install
npm run dev
```

## Community

- **Discord**: [Join the community](https://discord.gg/eKg4MhMkVJ)
- **Support**: [Buy Me a Coffee](https://buymeacoffee.com/jesposito)
- **Issues**: [GitHub Issues](https://github.com/jesposito/walkabout/issues)

## License

MIT
