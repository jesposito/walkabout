# Walkabout Implementation Plan

## Overview

Phased build approach: deliver value incrementally, validate each phase before adding complexity.

**Vision Pivot (2026-01-22):** Shifted from Google Flights scraping focus to Deal Feed Aggregation + Award Monitoring + Price Tracking. Single container, Unraid-first deployment.

---

## Phase 1: Deal Feed Aggregator (MVP)

**Goal:** Aggregate deal blogs, filter for your airport, send useful notifications.

**Duration:** 1-2 weeks

### Deliverables

1. **Data Model**
   - `user_profile` - home airport, timezone, watched destinations
   - `feed_source` - RSS feed URL, last fetch, enabled flag
   - `feed_item` - raw ingested items with fingerprint for dedup
   - `deal` - normalized deal with extracted price/route/dates
   - `deal_evidence` - links deal to source feed_items

2. **Services**
   - Feed fetcher (RSS parser with ETag/Last-Modified)
   - Deduplication (fingerprint-based)
   - Deal extractor (regex/heuristics for price, route, dates)
   - Notification sender (ntfy webhook)

3. **API Endpoints**
   - `GET /api/deals` - list deals filtered by user preferences
   - `POST /api/feeds` - add new feed source
   - `GET /api/status` - system health
   - `POST /api/dev/run/feeds` - manual trigger for testing

4. **UI (Minimal)**
   - Deal feed list view
   - Basic filtering (destination, date range)
   - Settings page (home airport, notification URL)

### Feed Sources (Initial)

| Source | URL | Update Frequency |
|--------|-----|------------------|
| Secret Flying | `secretflying.com/feed/` | Hourly |
| OMAAT Deals | `onemileatatime.com/deals/feed/` | Hourly |
| The Points Guy | `thepointsguy.com/deals/feed/` | Hourly |

### Success Criteria

- [ ] Ingests from 3+ feed sources without errors
- [ ] Deduplicates same deal across sources
- [ ] Filters deals to user's home airport
- [ ] Sends <5 notifications per day (not spammy)
- [ ] Dashboard loads in <2 seconds

---

## Phase 2: Award Flight Monitor

**Goal:** Track award availability via Seats.aero, alert on family-viable seats.

**Duration:** 1-2 weeks

### Deliverables

1. **Data Model**
   - `award_program` - loyalty program (United, Aeroplan, etc.)
   - `tracked_award_search` - user's award searches
   - `award_observation` - raw API results with hash for change detection

2. **Services**
   - Seats.aero API client
   - Change detector (hash comparison)
   - Award notification logic (min seats filter)

3. **API Endpoints**
   - `GET /api/awards` - current availability for tracked searches
   - `POST /api/awards/track` - add new award search
   - `POST /api/dev/run/awards` - manual trigger

4. **UI Additions**
   - Awards tab in navigation
   - Award search configuration
   - Availability display with date grid

### Seats.aero Integration Notes

- **Cost:** ~$10/month Pro subscription for API access
- **Rate limit:** ~1000 calls/day (use cached/bulk endpoints)
- **Coverage:** United, Aeroplan, Qantas FF, Velocity
- **Limitation:** Does NOT support Airpoints directly

### Success Criteria

- [ ] Polls Seats.aero within rate limits
- [ ] Detects availability changes accurately
- [ ] Filters for family-viable (4+ seats)
- [ ] Notifications only on meaningful changes

---

## Phase 3: Personal Price Tracker

**Goal:** Monitor your specific routes with historical price context.

**Duration:** 2-3 weeks

### Deliverables

1. **Data Model**
   - `tracked_route` - user's routes with date/passenger config
   - `price_observation` - time-series price data

2. **Services**
   - Price API client (Amadeus primary, Skyscanner backup)
   - Historical analysis (rolling average, percentile)
   - "Good price" scoring

3. **API Endpoints**
   - `GET /api/routes` - tracked routes
   - `POST /api/routes` - add tracked route
   - `GET /api/routes/{id}/history` - price history
   - `GET /api/routes/{id}/score` - current price vs history

4. **UI Additions**
   - History tab with price charts
   - Route configuration form
   - "Good/Average/High" price indicator

### Price API Options

| Provider | Free Tier | NZ Coverage | Notes |
|----------|-----------|-------------|-------|
| Amadeus | 2000 calls/month | Good | Cleanest API |
| Skyscanner (RapidAPI) | Limited | Good | Backup option |

### Success Criteria

- [ ] Accumulates 50+ price observations
- [ ] Price history chart renders correctly
- [ ] "Good price" indicator matches user intuition
- [ ] Alerts only on meaningful drops (>15% or new low)

---

## Phase 4: Smart Features

**Goal:** Polish UX with similarity suggestions, better scoring, and refinements.

**Duration:** 2-3 weeks

### Deliverables

1. **Similar Destinations**
   - Destination grouping (manual curation)
   - "Cheaper alternatives" suggestions
   
2. **Deal Scoring**
   - Relevance to user preferences
   - Historical context (how good is this deal?)
   - Source reputation weighting

3. **UX Polish**
   - Dark mode refinement
   - Mobile-optimized views
   - Keyboard shortcuts
   - Empty states and error handling

### Success Criteria

- [ ] Similar destination suggestions are useful (not noise)
- [ ] Deal scoring surfaces best deals first
- [ ] Mobile experience is usable
- [ ] Zero critical bugs

---

## Data Model Summary

```
┌─────────────────┐     ┌─────────────────┐
│  user_profile   │     │   feed_source   │
│  ───────────    │     │   ───────────   │
│  home_airport   │     │   url           │
│  timezone       │     │   last_fetch    │
│  watched_dests  │     │   enabled       │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   feed_item     │
                        │   ───────────   │
                        │   guid          │
                        │   title         │
                        │   content       │
                        │   fingerprint   │
                        └────────┬────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌─────────────────┐
│     deal        │◄────│  deal_evidence  │
│   ───────────   │     │   ───────────   │
│   origin/dest   │     │   deal_id       │
│   price         │     │   feed_item_id  │
│   dates         │     └─────────────────┘
│   confidence    │
└─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│  tracked_route  │────►│price_observation│
│   ───────────   │     │   ───────────   │
│   origin/dest   │     │   price         │
│   dates         │     │   observed_at   │
│   passengers    │     │   provider      │
└─────────────────┘     └─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│tracked_award    │────►│award_observation│
│   ───────────   │     │   ───────────   │
│   program       │     │   results_hash  │
│   route         │     │   payload       │
│   min_seats     │     │   observed_at   │
└─────────────────┘     └─────────────────┘
```

---

## Notification Architecture

### Signal Generation

```
Ingest → Normalize → Detect Change → Score → Filter → Notify
                          │              │        │
                          ▼              ▼        ▼
                     [signal]      [threshold]  [cooldown]
```

### Signal Types

| Type | Trigger | Priority |
|------|---------|----------|
| `NEW_DEAL` | New deal matches user prefs | Medium |
| `DEAL_UNICORN` | Deal >2σ below average | Critical |
| `PRICE_DROP` | Tracked route drops >15% | High |
| `AWARD_FOUND` | Award seats meet criteria | High |

### Cooldown Rules

- Same route: 24h minimum between alerts
- Same deal (across sources): dedupe by fingerprint
- Quiet hours: configurable (default 10pm-7am)

---

## Development Workflow

### Local Development

```bash
# Start with mock mode (no API calls)
MOCK_MODE=true docker-compose up

# Run specific service
docker-compose up backend

# View logs
docker-compose logs -f backend

# Run tests
docker-compose exec backend pytest
```

### Testing Endpoints

```bash
# Trigger feed fetch
curl -X POST http://localhost:8000/api/dev/run/feeds

# Check status
curl http://localhost:8000/api/dev/status

# View deals
curl http://localhost:8000/api/deals
```

### Database

```bash
# SQLite database location
./data/walkabout.db

# Backup
cp ./data/walkabout.db ./data/walkabout.db.backup

# Reset (dev only)
rm ./data/walkabout.db && docker-compose restart
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| RSS feeds change/break | Multiple sources, graceful degradation |
| Seats.aero rate limits | Cached endpoints, polling schedule |
| Price API quotas | Multiple providers, low-frequency polling |
| Alert fatigue | Cooldowns, scoring, sensitivity slider |
| Extraction accuracy | Store raw, improve parsers over time |

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| 1 | Deals surfaced/week | 10-20 |
| 1 | False positive rate | <20% |
| 2 | Award alerts/month | 2-5 |
| 3 | Price history points | 50+ |
| 4 | User engagement | 3-5 visits/week |
