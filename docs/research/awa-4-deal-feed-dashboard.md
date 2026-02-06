# Research: Deal Feed and Dashboard (awa.4)

## Executive Summary

The backend has a mature deals system: 14 RSS feed sources, AI-enhanced parsing, deal rating (Hot/Good/Decent/Normal/Above Market), relevance filtering (Local/Regional/Hub), and comprehensive API endpoints. The frontend has placeholder pages and 8 shared components ready. The main work is building DealCard, DealsList, filters, and wiring them to existing APIs.

## Backend API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/deals/api/deals` | GET | Paginated deals (origin, relevant, limit, offset) |
| `/deals/api/deals/{id}/dismiss` | POST | Dismiss a deal |
| `/deals/api/deals/{id}/restore` | POST | Restore dismissed deal |
| `/deals/api/health/feeds` | GET | Feed health status |
| `/deals/api/ingest` | POST | Trigger manual ingestion |
| `/deals/api/rate-deals` | POST | Rate unrated deals |
| `/deals/api/insights` | GET | AI-generated dashboard insights |

## Deal Model Fields

Key fields: id, source (DealSource enum), link, published_at, raw_title, parsed_origin, parsed_destination, parsed_price, parsed_currency, parsed_airline, parsed_cabin_class, is_relevant, relevance_reason, score (0-100 composite), deal_rating (savings %), rating_label (emoji label), market_price, market_currency, market_price_source.

## Rating System

| Label | Threshold | Badge Variant |
|-------|-----------|---------------|
| Hot Deal | 30%+ savings | `hot` (green #00ff88) |
| Good Deal | 15-29% savings | `good` (cyan #22d3ee) |
| Decent | 5-14% savings | `decent` (purple #a78bfa) |
| Normal | 0-4% savings | `normal` (gray #999) |
| Above Market | negative savings | `above` (red #ef4444) |

## Relevance Categories

- **Local**: From user's home airport (AKL, WLG, CHC, etc.)
- **Regional**: From AU/NZ/Pacific hubs (SYD, BNE, MEL, NAN, HNL)
- **Hub**: From major international hubs (LAX, SFO, JFK, SIN, HKG, NRT, DOH, LHR)

## Scoring System (0-100)

- Relevance: 40 pts (home=40, watched=35, similar=25, region=15, other=10)
- Value: 30 pts (cheaper = higher)
- Recency: 20 pts (<6h=20, decays to 5 for 7+ days)
- Quality: 10 pts (airline prestige)

## API Response Gap

TypeScript `Deal` interface uses `url` but backend sends `link`. Missing fields: airline, cabin_class, published_at, is_relevant, relevance_reason. Needs update.

## Components to Build

1. **DealCard** - Source badge, rating badge, route info, price, airline, actions (dismiss/book)
2. **DealsList** - Paginated container with loading/empty states
3. **PriceSparkline** - Deal price vs market price visual comparison
4. **DealFilters** - Filter by source, cabin, relevance
5. **DealSortControls** - Sort by rating, price, date
6. **FeedHealthWidget** - Feed status on dashboard (optional)

## Files Reviewed

- `backend/app/api/deals.py`, `backend/app/models/deal.py`, `backend/app/models/feed_health.py`
- `backend/app/services/deal_rating.py`, `backend/app/services/deal_scorer.py`
- `backend/app/services/feeds/feed_service.py`, `backend/app/services/feeds/base.py`
- `backend/app/services/relevance.py`
- `frontend/src/api/client.ts`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Deals.tsx`
- All shared components in `frontend/src/components/shared/`
