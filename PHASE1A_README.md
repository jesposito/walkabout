# Walkabout Phase 1a - Prove Ingestion

This is Phase 1a - the minimal viable system proving that scraping works reliably and deal aggregation provides value.

## Current Features

| Feature | Status |
|---------|--------|
| Deal RSS Aggregation | Multi-source (Secret Flying, OMAAT, TPG, regional) |
| AI Deal Parsing | Optional - Claude API or local Ollama |
| Google Flights Scraper | Playwright with stealth mode |
| Price Analysis | Robust z-score (median/MAD) + new low detection |
| Scrape Health | Circuit breaker, failure classification, auto-recovery |
| Trip Plans | Multi-origin/dest, flexible dates, budget constraints |
| Notifications | ntfy and Discord webhook support |
| Settings UI | Full web-based configuration |
| Deal Rating | Market price comparison with rating labels |

## What's NOT Yet Implemented

| Feature | Status | Notes |
|---------|--------|-------|
| Award Monitoring | Considering | Seats.aero integration for points availability |
| TimescaleDB | Deferred | Time-series optimization |
| Celery + Redis | Deferred | Distributed job processing |
| React Frontend | Deferred | Currently using server-rendered Jinja2 |
| Calendar Heatmaps | Deferred | Visual price trends |
| Multi-user | Deferred | Currently single-user |

## Architecture

```
Phase 1a Stack (Single Container):
┌─────────────────────────────────────────────────────────────┐
│  FastAPI + Playwright + SQLite + APScheduler                │
│                                                             │
│  ├─ Deal Feeds (RSS parsing)                                │
│  ├─ Price Scraping (Google Flights via Playwright)          │
│  ├─ Price Analysis (robust z-score)                         │
│  ├─ Trip Matching (flexible date search)                    │
│  ├─ Notifications (ntfy/Discord)                            │
│  └─ Server-rendered UI (Jinja2 + HTMX)                      │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Run the container
docker run -d \
  --name walkabout \
  -p 8000:8000 \
  -v /path/to/data:/app/data \
  -e TZ=Pacific/Auckland \
  ghcr.io/jesposito/walkabout:latest

# Access the dashboard
open http://localhost:8000/
```

## Configuration

All settings are configured via the **Settings** page (`/settings`):

- **Home Airports**: Your departure airports for deal filtering
- **AI Provider**: Optional Claude or Ollama for enhanced deal parsing
- **Notifications**: ntfy server or Discord webhook
- **Notification Preferences**: Quiet hours, cooldowns, filters

## Key Technical Decisions

From Oracle Review feedback:

| Decision | Rationale |
|----------|-----------|
| SQLite over PostgreSQL | Simpler deployment, good enough for single-user |
| APScheduler over Celery | No Redis dependency, sufficient for single container |
| Server HTML over React | Faster iteration, works without JS |
| Robust z-score | Uses median/MAD instead of mean/stddev for outlier resistance |
| Circuit breaker | Protects against scraping failures cascading |

## Success Metrics

Phase 1a is considered successful when:

- 7+ days continuous operation without intervention
- <10% scrape failure rate
- Deal notifications delivered within 5 minutes
- System alerts working (stale data, failures)

## Phase 1b Planning

When ready to expand:

- **Award Monitoring**: Integrate Seats.aero API for points availability
- **Better Analytics**: TimescaleDB for time-series queries
- **Distributed Jobs**: Celery + Redis for scaling
- **Modern Frontend**: React SPA with better interactivity

## Useful Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/` | Dashboard with deals |
| `/trips` | Trip plan management |
| `/settings` | Configuration |
| `/about` | Version and links |
| `/health` | Health check endpoint |

## Logs & Debugging

```bash
# View container logs
docker logs -f walkabout

# Check for scrape failures
docker logs walkabout 2>&1 | grep -i "scrape\|failure"

# Check notification activity
docker logs walkabout 2>&1 | grep -i "notification"
```
