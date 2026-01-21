# Walkabout

**Personal Flight Deal Hub** - A self-hosted dashboard that aggregates flight deals, tracks award availability, and monitors prices for your specific routes.

```
Your flight intelligence, your data, your server.
```

## What It Does

| Feature | Description |
|---------|-------------|
| **Deal Aggregator** | Pulls deals from Secret Flying, OMAAT, TPG and filters for your home airport |
| **Award Monitor** | Tracks points availability via Seats.aero for partner programs |
| **Price Tracker** | Monitors your specific routes with historical context |
| **Smart Alerts** | Notifications via ntfy when deals match your criteria |
| **Similar Destinations** | "You want Fiji? Rarotonga is 40% cheaper right now" |

## Why Not Just Use Google Flights Alerts?

Google is great for what it does. Walkabout fills the gaps:

- **Aggregated deal feeds** - One place for Secret Flying, OMAAT, TPG, etc.
- **Award flight tracking** - Points availability that Google doesn't show
- **Your historical context** - "Is this actually a good price for MY route?"
- **Destination flexibility** - Similar/alternative destination suggestions
- **Self-hosted** - Your data stays on your server

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
docker-compose -f docker-compose.single.yml up -d
```

2. **Open the dashboard**: `http://your-server:8080`

3. **Set your profile**:
   - Home airport (e.g., AKL)
   - Destinations you care about
   - Notification preferences

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `HOME_AIRPORT` | Your departure airport (IATA code) | `AKL` |
| `WATCHED_DESTINATIONS` | Comma-separated destinations | `SYD,NAN,HNL,TYO` |
| `TZ` | Your timezone | `Pacific/Auckland` |
| `NOTIFICATION_URL` | ntfy/webhook URL for alerts | - |
| `SEATS_AERO_API_KEY` | For award flight monitoring | - |
| `DEAL_THRESHOLD_PERCENT` | Alert on deals this % below average | `20` |

## Architecture

Single container, simple stack:

```
┌─────────────────────────────────────────────────────────────┐
│                    walkabout (single container)             │
├─────────────────────────────────────────────────────────────┤
│  FastAPI        │  APScheduler      │  SQLite               │
│  (API + UI)     │  (background jobs)│  (all data)           │
├─────────────────────────────────────────────────────────────┤
│  Services:                                                  │
│  - Feed Aggregator (RSS from deal sites)                    │
│  - Award Monitor (Seats.aero API)                           │
│  - Price Tracker (Amadeus/Skyscanner)                       │
│  - Deal Matcher (your routes + preferences)                 │
│  - Notifier (ntfy/webhook)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Data Sources

### Deal Feeds (RSS)
- Secret Flying - `secretflying.com/feed/`
- One Mile at a Time - deals RSS
- The Points Guy - deals section
- Australian Frequent Flyer - covers NZ routes

### Award Availability
- **Seats.aero** ($10/mo Pro subscription)
- Tracks: United, Aeroplan, Qantas FF, Velocity
- Note: Does NOT track Airpoints directly, but partner programs can book Air NZ metal

### Price Data
- Amadeus API (free tier)
- Skyscanner via RapidAPI (free tier)

## Documentation

- [Vision & Product](docs/VISION.md) - Product vision and positioning
- [Architecture](docs/ARCHITECTURE.md) - Data model and technical design
- [UX Design](docs/UX_DESIGN.md) - User flows and interface design
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Phased build approach

## Development

```bash
# Run with mock data (no API calls)
MOCK_MODE=true docker-compose up

# Run tests
docker-compose exec backend pytest

# View logs
docker-compose logs -f backend
```

## Unraid Installation

See [UNRAID_DEPLOYMENT.md](UNRAID_DEPLOYMENT.md) for detailed Unraid setup instructions.

Template available in `unraid/walkabout-template.xml`.

## License

MIT
