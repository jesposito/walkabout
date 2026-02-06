# Research: Watchlist & Trip Management UI (awa-6)

## Overview

This document covers the backend models, API endpoints, frontend components, and gap analysis for the Watchlist and Trip Management feature. The backend is fully built with comprehensive CRUD APIs. The frontend is scaffolded with placeholder pages and a mature shared component library, but all Watchlist and Trip Management UI is unimplemented.

---

## 1. SearchDefinition Model & API

### Model: `backend/app/models/search_definition.py`

SearchDefinition is the core entity for price-comparable route monitoring. Each definition fully specifies search parameters so prices scraped at different times are comparable.

#### Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `id` | Integer (PK) | auto | |
| `origin` | String(3) | required | IATA code, indexed |
| `destination` | String(3) | required | IATA code, indexed |
| `trip_type` | Enum(TripType) | `round_trip` | `round_trip`, `one_way` |
| `departure_date_start` | Date | null | Fixed date mode |
| `departure_date_end` | Date | null | Fixed date mode |
| `departure_days_min` | Integer | null | Rolling window mode (days from now) |
| `departure_days_max` | Integer | null | Rolling window mode |
| `trip_duration_days_min` | Integer | null | For round trips |
| `trip_duration_days_max` | Integer | null | |
| `adults` | Integer | 2 | |
| `children` | Integer | 2 | Ages 2-11 |
| `infants_in_seat` | Integer | 0 | |
| `infants_on_lap` | Integer | 0 | |
| `cabin_class` | Enum(CabinClass) | `economy` | `economy`, `premium_economy`, `business`, `first` |
| `stops_filter` | Enum(StopsFilter) | `any` | `any`, `nonstop`, `one_stop`, `two_plus` |
| `include_airlines` | String(100) | null | Comma-separated IATA codes |
| `exclude_airlines` | String(100) | null | Comma-separated IATA codes |
| `currency` | String(3) | `NZD` | |
| `locale` | String(10) | `en-NZ` | Affects point of sale |
| `carry_on_bags` | Integer | 0 | |
| `checked_bags` | Integer | 0 | |
| `name` | String(100) | null | Human-friendly name |
| `is_active` | Boolean | true | |
| `scrape_frequency_hours` | Integer | 12 | |
| `preferred_source` | String(20) | `auto` | `auto`, `serpapi`, `skyscanner`, `amadeus`, `playwright` |
| `version` | Integer | 1 | Version tracking |
| `parent_id` | Integer | null | Reference to previous version |
| `created_at` | DateTime(tz) | now() | |
| `updated_at` | DateTime(tz) | on update | |

#### Relationships

- `prices` -> `FlightPrice[]` (one-to-many)
- `scrape_health` -> `ScrapeHealth` (one-to-one)

#### Computed Properties

- `total_passengers` -> sum of adults + children + infants_in_seat + infants_on_lap
- `display_name` -> name or `"{origin}-{destination} ({total_passengers}pax, {cabin_class})"`

### API Endpoints (mounted at `/prices`)

| Method | Path | Purpose | Request Body |
|--------|------|---------|--------------|
| GET | `/prices/searches` | List search definitions | `?active_only=true` |
| POST | `/prices/searches` | Create search definition | `SearchDefinitionCreate` |
| GET | `/prices/searches/{id}` | Get single definition | - |
| DELETE | `/prices/searches/{id}` | Deactivate (soft delete) | - |
| GET | `/prices/searches/{id}/prices` | Price history | `?days=30&departure_date=` |
| GET | `/prices/searches/{id}/stats` | Price statistics | `?days=90` |
| GET | `/prices/searches/{id}/latest` | Latest N prices | `?limit=10` |
| GET | `/prices/searches/{id}/options` | Unique flight options w/ booking URLs | `?limit=3` |
| PUT | `/prices/searches/{id}/frequency` | Update scrape frequency | `{ frequency_hours: int }` |
| PUT | `/prices/searches/{id}/source` | Update preferred source | `{ preferred_source: str }` |
| POST | `/prices/searches/{id}/refresh` | Trigger manual price refresh | - |

#### SearchDefinitionCreate Schema

```python
{
    origin: str,                     # required
    destination: str,                # required
    trip_type: str = "round_trip",
    adults: int = 2,
    children: int = 2,
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    cabin_class: str = "economy",
    stops_filter: str = "any",
    currency: str = "NZD",
    name: str | None = None,
    departure_days_min: int | None = 60,
    departure_days_max: int | None = 120,
    trip_duration_days_min: int | None = 7,
    trip_duration_days_max: int | None = 14,
}
```

#### SearchDefinitionResponse Schema

```python
{
    id: int,
    origin: str,
    destination: str,
    trip_type: str,
    adults: int,
    children: int,
    cabin_class: str,
    stops_filter: str,
    currency: str,
    name: str | None,
    is_active: bool,
    created_at: datetime | None,
}
```

#### PriceStats Response

```python
{
    search_definition_id: int,
    min_price: Decimal | None,
    max_price: Decimal | None,
    avg_price: Decimal | None,
    current_price: Decimal | None,
    price_count: int,
    price_trend: str | None,  # "up", "down", "stable"
}
```

---

## 2. TripPlan Model & API

### Model: `backend/app/models/trip_plan.py`

TripPlan is a flexible "dream trip" specification that supports multiple origins, destinations, destination types, date ranges, and budget constraints. It is not a 1:1 relationship with SearchDefinition -- TripPlans are higher-level and can expand to multiple concrete searches.

#### Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `id` | Integer (PK) | auto | |
| `name` | String(128) | required | |
| `origins` | JSON (list) | [] | IATA codes |
| `destinations` | JSON (list) | [] | IATA codes |
| `destination_types` | JSON (list) | [] | e.g., `["tropical", "japan"]` |
| `available_from` | DateTime | null | Travel window start |
| `available_to` | DateTime | null | Travel window end |
| `trip_duration_min` | Integer | 3 | Min days |
| `trip_duration_max` | Integer | 14 | Max days |
| `budget_max` | Integer | null | Max budget |
| `budget_currency` | String(3) | `NZD` | |
| `travelers_adults` | Integer | 2 | |
| `travelers_children` | Integer | 0 | |
| `cabin_classes` | JSON (list) | [] | e.g., `["economy", "business"]` |
| `is_active` | Boolean | true | |
| `notify_on_match` | Boolean | true | |
| `check_frequency_hours` | Integer | 12 | |
| `notes` | Text | null | |
| `match_count` | Integer | 0 | Computed |
| `last_match_at` | DateTime | null | |
| `search_in_progress` | Boolean | false | Concurrency lock |
| `search_started_at` | DateTime | null | |
| `last_search_at` | DateTime | null | |
| `created_at` | DateTime | now() | |
| `updated_at` | DateTime | now() | |

#### Relationships

- `matches` -> `TripPlanMatch[]` (one-to-many, cascade delete, ordered by match_score desc)

### TripPlanMatch Model: `backend/app/models/trip_plan_match.py`

Persists the best flight matches for each Trip Plan from any source.

| Field | Type | Notes |
|-------|------|-------|
| `id` | Integer (PK) | |
| `trip_plan_id` | FK -> trip_plans | cascade delete |
| `source` | String(50) | `google_flights`, `rss_deal`, `seats_aero`, `amadeus` |
| `deal_id` | FK -> deals | nullable, SET NULL on delete |
| `origin` | String(10) | |
| `destination` | String(10) | |
| `departure_date` | Date | |
| `return_date` | Date | nullable |
| `price_nzd` | Numeric(10,2) | Always NZD |
| `original_price` | Numeric(10,2) | nullable |
| `original_currency` | String(3) | nullable |
| `airline` | String(100) | nullable |
| `stops` | Integer | default 0 |
| `duration_minutes` | Integer | nullable |
| `booking_url` | Text | nullable |
| `match_score` | Numeric(5,2) | 0-100 |
| `deal_title` | String(500) | nullable |
| `found_at` | DateTime | now() |
| `updated_at` | DateTime | now() |

Computed properties: `is_expired`, `days_until_departure`

### API Endpoints (mounted at `/trips`)

| Method | Path | Purpose | Request Body |
|--------|------|---------|--------------|
| GET | `/trips/` | Server-rendered trips HTML page | - |
| GET | `/trips/api/trips` | List trip plans (JSON) | `?active_only=false` |
| POST | `/trips/api/trips` | Create trip plan | `TripPlanCreate` |
| GET | `/trips/api/trips/{id}` | Get single trip | - |
| PUT | `/trips/api/trips/{id}` | Update trip plan | `TripPlanCreate` |
| DELETE | `/trips/api/trips/{id}` | Delete trip (hard delete) | - |
| PUT | `/trips/api/trips/{id}/toggle` | Toggle is_active | - |
| GET | `/trips/api/trips/{id}/matches` | Get RSS deal matches | `?limit=20` |
| POST | `/trips/api/trips/{id}/search` | Trigger Google Flights search (background) | - |
| POST | `/trips/api/trips/{id}/check-matches` | Re-check RSS deal matches | - |

#### TripPlanCreate Schema

```python
{
    name: str,                        # required
    origins: list[str] = [],
    destinations: list[str] = [],
    destination_types: list[str] = [],
    available_from: datetime | None = None,
    available_to: datetime | None = None,
    trip_duration_min: int = 3,
    trip_duration_max: int = 14,
    budget_max: int | None = None,
    budget_currency: str = "NZD",
    cabin_classes: list[str] = ["economy"],
    travelers_adults: int = 2,
    travelers_children: int = 0,
    notify_on_match: bool = True,
    check_frequency_hours: int = 12,
    notes: str | None = None,
}
```

### SearchDefinition vs TripPlan Relationship

These are **separate entities** with no direct FK relationship:

| Aspect | SearchDefinition | TripPlan |
|--------|-----------------|----------|
| Purpose | Exact route monitoring with comparable prices | Flexible "dream trip" with broad criteria |
| Origins | Single origin IATA code | Multiple origins (JSON array) |
| Destinations | Single destination IATA code | Multiple destinations + destination types |
| Dates | Fixed dates or rolling window | Travel availability window |
| Price tracking | Direct FlightPrice series | TripPlanMatch results from multiple sources |
| Matching | N/A | Matches against RSS deals + Google Flights searches |

---

## 3. ScrapeHealth Model

### Model: `backend/app/models/scrape_health.py`

First-class scrape health tracking per SearchDefinition.

| Field | Type | Notes |
|-------|------|-------|
| `id` | Integer (PK) | |
| `search_definition_id` | FK -> search_definitions | unique, cascade delete |
| `total_attempts` | Integer | 0 |
| `total_successes` | Integer | 0 |
| `total_failures` | Integer | 0 |
| `consecutive_failures` | Integer | 0 |
| `last_attempt_at` | DateTime(tz) | |
| `last_success_at` | DateTime(tz) | |
| `last_failure_at` | DateTime(tz) | |
| `last_failure_reason` | String(50) | captcha, timeout, layout_change, no_results, blocked, unknown |
| `last_failure_message` | Text | |
| `last_screenshot_path` | String(500) | |
| `last_html_snapshot_path` | String(500) | |
| `stale_alert_sent_at` | DateTime(tz) | |
| `circuit_open` | Integer | 0=closed, 1=open |
| `circuit_opened_at` | DateTime(tz) | |

#### Computed Properties

- `success_rate` -> percentage (float)
- `is_healthy` -> bool (circuit closed, <3 consecutive failures, >50% success rate if 10+ attempts)

#### Methods

- `record_success()` -> increments counters, resets consecutive_failures, closes circuit
- `record_failure(reason, message, screenshot_path, html_snapshot_path)` -> increments counters, opens circuit after 5 consecutive failures

### API Exposure

ScrapeHealth is currently only exposed through the server-rendered status page (`/` route in `status.py`), which shows health data per search definition. There is **no dedicated JSON API endpoint** for scrape health data -- it is accessed via the `SearchDefinition.scrape_health` relationship.

---

## 4. Airport Data & Autocomplete

### Service: `backend/app/services/airports.py`

#### Data Source

- Primary: `backend/app/resources/airports.dat` (CSV, ~6000+ airports)
- Fallback: 40+ hardcoded major airports
- In-memory dictionaries: `AIRPORTS`, `CITY_TO_CODES`, `COUNTRY_TO_CODES`

#### Airport Dataclass

```python
@dataclass
class Airport:
    code: str    # IATA 3-letter
    name: str    # Airport name
    city: str    # City
    country: str # Country
    region: str  # Oceania, Asia, Europe, North America, South America, Africa
```

#### AirportService Methods

| Method | Purpose |
|--------|---------|
| `is_valid(code)` -> bool | Check if IATA code exists |
| `validate(code)` -> (bool, error) | Validate with suggestions on failure |
| `search(query, limit=10)` -> Airport[] | Fuzzy search by code, city, country, name, region |
| `get(code)` -> Airport | Direct lookup |
| `get_by_region(region)` -> Airport[] | All airports in a region |
| `get_by_country(country)` -> Airport[] | All airports in a country |
| `code_for_city(city)` -> str | Resolve city name/alias to code |

#### AirportLookup Class

Text analysis utility for finding airports in free-text strings (used by deal parsing):
- `find_locations(text)` -> list of (code, position, match_type)
- `extract_route(text)` -> (origin, destination)

#### API Endpoints (mounted at `/settings`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/settings/api/airports/search?q=auck&limit=10` | Airport autocomplete search |
| GET | `/settings/api/airports/{code}` | Get single airport details |

#### Airport Search Response

```json
{
    "results": [
        {
            "code": "AKL",
            "name": "Auckland International",
            "city": "Auckland",
            "country": "New Zealand",
            "region": "Oceania",
            "label": "AKL - Auckland, New Zealand"
        }
    ]
}
```

#### Supporting Services

- `DestinationService` (`destinations.py`): Groups airports into geographic regions (south_pacific_islands, australia_east, japan, etc.), provides `get_similar_airports()`, `expand_watched_destinations()`
- `DestinationTypeService` (`destination_types.py`): Semantic destination types (tropical, family, adventure, city_break, honeymoon, etc.) with airport and keyword mappings. Used by TripPlan matching.

---

## 5. Existing Frontend

### Framework & Libraries

- React 18 + TypeScript
- Vite 5 build tool
- Tailwind CSS 3.4 (custom design system with `deck-*` tokens)
- React Router 6 (client-side routing)
- TanStack React Query 5 (data fetching/caching)
- Recharts 2 (charting)
- Axios (HTTP client)

### Current Routes (`App.tsx`)

| Path | Component | Status |
|------|-----------|--------|
| `/` | `Dashboard` | Placeholder (EmptyState) |
| `/watchlist` | `Watchlist` | Placeholder (EmptyState) |
| `/deals` | `Deals` | Placeholder (EmptyState) |
| `/history` | `History` | Placeholder (EmptyState) |
| `/settings` | `Settings` | Placeholder cards (coming soon text) |

### App Shell (`AppShell.tsx`)

- Desktop: left sidebar (256px) with SVG icon nav links
- Mobile: bottom tab bar with 5 items (Dashboard, Watchlist, Deals, History, Settings)
- `Outlet` for page content, max-width 5xl container

### Shared Components (`frontend/src/components/shared/`)

| Component | Props | Notes |
|-----------|-------|-------|
| `Badge` | variant: hot/good/decent/normal/above/info | Colored pill badges |
| `Button` | variant: primary/secondary/ghost, size: sm/md/lg | Styled buttons |
| `Card` | interactive?, className, onClick | Surface container with border |
| `EmptyState` | icon, title, description, actionLabel, onAction | Empty state display |
| `Input` | label, error, ...HTMLInputAttributes | Form input with label/error |
| `PageHeader` | title, subtitle, actions (ReactNode) | Page header with action slot |
| `PriceDisplay` | price, currency, size, trend | Formatted currency display |
| `Spinner` | size: sm/md/lg | Loading spinner |

### Existing Feature Components

| Component | Purpose |
|-----------|---------|
| `RouteCard` | Displays a SearchDefinition with price stats grid and PriceChart |
| `PriceChart` | 30-day price history line chart using Recharts |

### Existing API Client Functions (`frontend/src/api/client.ts`)

#### Search Definitions (Watchlist)

| Function | Endpoint | Notes |
|----------|----------|-------|
| `fetchSearchDefinitions(activeOnly)` | GET `/prices/searches` | |
| `fetchSearchDefinition(id)` | GET `/prices/searches/{id}` | |
| `createSearchDefinition(search)` | POST `/prices/searches` | |
| `deleteSearchDefinition(id)` | DELETE `/prices/searches/{id}` | |

#### Prices

| Function | Endpoint | Notes |
|----------|----------|-------|
| `fetchPriceHistory(searchId, days)` | GET `/prices/searches/{id}/prices` | |
| `fetchPriceStats(searchId)` | GET `/prices/searches/{id}/stats` | |
| `fetchFlightOptions(searchId, limit)` | GET `/prices/searches/{id}/options` | |
| `refreshPrices(searchId)` | POST `/prices/searches/{id}/refresh` | |

#### Deals

| Function | Endpoint | Notes |
|----------|----------|-------|
| `fetchDeals(limit)` | GET `/deals/api/deals` | |
| `dismissDeal(id)` | POST `/deals/api/deals/{id}/dismiss` | |

#### Settings

| Function | Endpoint | Notes |
|----------|----------|-------|
| `fetchSettings()` | GET `/settings/api/settings` | |
| `updateSettings(settings)` | PUT `/settings/api/settings` | |

#### Missing from Client (backend exists but no frontend function)

- All Trip Plan CRUD (`/trips/api/trips*`)
- Airport search (`/settings/api/airports/search`)
- Airport detail (`/settings/api/airports/{code}`)
- Scrape health data (no JSON API exists)
- Trip plan matches, search trigger, toggle, check-matches
- Search definition frequency/source updates
- Destination types listing

### TypeScript Interfaces Defined

- `SearchDefinition` -- matches backend response
- `FlightPrice` -- price data point
- `PriceStats` -- min/max/avg/current/trend
- `Deal` -- RSS deal
- `UserSettings` -- home_airport, notification_enabled, ntfy_topic

### Missing TypeScript Interfaces

- `TripPlan`
- `TripPlanMatch`
- `Airport` (for autocomplete)
- `ScrapeHealth`

---

## 6. Gap Analysis: What Needs to Be Built

### Backend Gaps

The backend is **essentially complete** for this feature. Minor additions:

1. **Scrape health JSON API**: Currently only exposed via server-rendered HTML. Need a JSON endpoint (e.g., `GET /prices/searches/{id}/health`) for the React frontend to display health status per watchlist item.
2. **Destination types listing API**: Need a `GET /api/destination-types` endpoint so the Trip Plan form can show available types. The `DestinationTypeService.get_all_types()` method exists but has no API endpoint.
3. **Airport search API is on `/settings/` prefix**: The frontend will need to call `/settings/api/airports/search` -- this works but is slightly awkward. No change required, just note the path.

### Frontend Gaps (Everything Below Needs Building)

#### A. API Client Additions (`client.ts`)

New functions needed:

```typescript
// Trip Plans
fetchTripPlans(activeOnly?: boolean): Promise<TripPlan[]>
fetchTripPlan(id: number): Promise<TripPlan>
createTripPlan(plan: TripPlanCreate): Promise<TripPlan>
updateTripPlan(id: number, plan: TripPlanCreate): Promise<TripPlan>
deleteTripPlan(id: number): Promise<void>
toggleTripPlan(id: number): Promise<{ is_active: boolean }>
searchTripPlan(id: number): Promise<{ status: string; message: string }>
fetchTripPlanMatches(id: number, limit?: number): Promise<TripPlanMatchResponse>
checkTripPlanMatches(id: number): Promise<MatchCheckResponse>

// Airports
searchAirports(query: string, limit?: number): Promise<Airport[]>
getAirport(code: string): Promise<Airport>

// Destination Types (needs backend endpoint)
fetchDestinationTypes(): Promise<DestinationType[]>

// Scrape Health (needs backend endpoint)
fetchScrapeHealth(searchId: number): Promise<ScrapeHealth>
```

New TypeScript interfaces needed:

```typescript
interface TripPlan {
  id: number
  name: string
  origins: string[]
  destinations: string[]
  destination_types: string[]
  available_from: string | null
  available_to: string | null
  trip_duration_min: number
  trip_duration_max: number
  budget_max: number | null
  budget_currency: string
  cabin_classes: string[]
  travelers_adults: number
  travelers_children: number
  is_active: boolean
  notify_on_match: boolean
  check_frequency_hours: number
  match_count: number
  last_match_at: string | null
  notes: string | null
  created_at: string
  search_in_progress: boolean
}

interface TripPlanMatch {
  id: number
  trip_plan_id: number
  source: string
  origin: string
  destination: string
  departure_date: string
  return_date: string | null
  price_nzd: number
  airline: string | null
  stops: number
  duration_minutes: number | null
  booking_url: string | null
  match_score: number
  deal_title: string | null
  found_at: string
}

interface Airport {
  code: string
  name: string
  city: string
  country: string
  region: string
  label: string
}

interface ScrapeHealth {
  total_attempts: number
  total_successes: number
  total_failures: number
  consecutive_failures: number
  success_rate: number
  is_healthy: boolean
  last_success_at: string | null
  last_failure_reason: string | null
}
```

#### B. Watchlist Page (`Watchlist.tsx`)

Currently a placeholder. Needs:

1. **SearchDefinition List View**
   - Fetch and display all active search definitions using `RouteCard` component
   - Show scrape health indicator per route (green/yellow/red dot)
   - Actions: pause/resume, delete, refresh prices, edit frequency
   - Empty state with "Add a route" CTA (already has EmptyState placeholder)

2. **Add Route Form/Modal**
   - Airport autocomplete inputs for origin and destination (use `/settings/api/airports/search`)
   - Trip type selector (round_trip / one_way)
   - Passenger counts (adults, children, infants)
   - Cabin class selector
   - Stops filter selector
   - Optional name field
   - Departure window (days from now range or fixed dates)
   - Trip duration range
   - Submit creates SearchDefinition via `POST /prices/searches`

3. **Route Detail View** (could be expandable card or separate sub-route)
   - Full price stats display (current, average, min, max, trend)
   - Price history chart (PriceChart already exists)
   - Flight options with booking links
   - Scrape health details
   - Configuration controls (frequency, source preference)

#### C. Trip Plans Page (New Page or Tab)

No page currently exists in the router. Needs either:
- A new `/trips` route and page, OR
- A tab/section within the Watchlist page

Components needed:

1. **TripPlan List View**
   - Cards showing each trip plan with name, origins, destinations, budget, match count
   - Active/inactive badge
   - Search status indicator (in_progress spinner)
   - Last match timestamp
   - Actions: edit, delete, toggle active, trigger search, check matches

2. **Add/Edit Trip Plan Form**
   - Name input
   - Multi-airport picker for origins (autocomplete, add multiple)
   - Multi-airport picker for destinations (autocomplete, add multiple)
   - Destination type picker (checkboxes/pills for tropical, japan, europe, etc.)
   - Date range picker for travel availability window
   - Trip duration range (min/max days slider or inputs)
   - Budget input with currency selector
   - Cabin class multi-select
   - Traveler counts (adults, children)
   - Notification toggle
   - Check frequency selector
   - Notes textarea

3. **Trip Plan Detail / Matches View**
   - Best flight matches (TripPlanMatch cards with price, dates, airline, booking link)
   - RSS deal matches with relevance scores
   - "Search Now" button to trigger background Google Flights search
   - Search status indicator
   - Match score visualization

#### D. Shared Components Needed

| Component | Purpose |
|-----------|---------|
| `AirportAutocomplete` | Debounced search input calling `/settings/api/airports/search`, shows dropdown with code/city/country |
| `MultiAirportPicker` | Wraps AirportAutocomplete for selecting multiple airports (used by TripPlan origins/destinations) |
| `DestinationTypePicker` | Grid/list of destination type chips with emoji + name (tropical, japan, etc.) |
| `DateRangePicker` | Two date inputs for from/to ranges |
| `NumberRangeInput` | Min/max number inputs (for trip duration, departure days) |
| `SelectInput` | Styled select/dropdown matching design system (for cabin class, stops filter, trip type) |
| `Modal` or `SlideOver` | Overlay container for forms (add route, add trip plan) |
| `HealthIndicator` | Small dot/badge showing scrape health status (green/yellow/red) |
| `MatchCard` | Displays a TripPlanMatch with price, route, dates, airline, booking link |
| `ConfirmDialog` | Delete confirmation dialog |

#### E. Router Updates (`App.tsx`)

Need to add a trips route if it's a separate page:
```tsx
<Route path="/trips" element={<Trips />} />
```

Or alternatively, make the Watchlist page handle both concepts with tabs/sections.

---

## 7. Design Considerations

### Design System Tokens (from Tailwind config)

The app uses a custom dark theme with these token families:
- `deck-bg`, `deck-surface`, `deck-surface-hover`, `deck-border`, `deck-text-primary`, `deck-text-secondary`, `deck-text-muted`
- `accent-primary`, `accent-primary-dim`, `accent-secondary`
- `deal-hot`, `deal-good`, `deal-decent`, `deal-above`
- `text-price-sm`, `text-price-md`, `text-price-lg`
- `rounded-card` border radius
- `min-h-touch`, `min-w-touch` for mobile tap targets

### Mobile Considerations

- Bottom tab bar is fixed with 5 items (Dashboard, Watchlist, Deals, History, Settings)
- Adding a "Trips" tab would require either replacing an item or combining with Watchlist
- Forms should be full-screen on mobile (modal/slide-over)
- Touch targets must be `min-h-touch` (44px)

### Data Flow

```
User creates SearchDefinition
    -> Backend stores + starts scheduled scraping
    -> FlightPrice records accumulate over time
    -> Frontend fetches stats/history via API
    -> PriceChart renders trend
    -> ScrapeHealth tracks reliability

User creates TripPlan
    -> TripMatcher scores RSS deals against plan criteria
    -> TripPlanSearchService expands criteria to Google Flights searches
    -> TripPlanMatch records persisted (top N per destination)
    -> Frontend shows consolidated matches from all sources
```

---

## 8. Implementation Priority

### Phase 1: Watchlist Core
1. Add missing TypeScript interfaces and API client functions
2. Implement Watchlist page with SearchDefinition list (using existing RouteCard)
3. Build AirportAutocomplete component
4. Build Add Route form/modal
5. Add delete/pause/resume actions

### Phase 2: Watchlist Enhancement
1. Add scrape health indicator (may need backend endpoint)
2. Add route detail expansion with flight options + booking links
3. Add frequency/source configuration controls
4. Add manual price refresh button

### Phase 3: Trip Plans
1. Add Trip Plan API client functions
2. Build Trip Plan list page/section
3. Build MultiAirportPicker, DestinationTypePicker
4. Build Add/Edit Trip Plan form
5. Build Trip Plan match display
6. Add search trigger + status indicator

### Phase 4: Integration
1. Dashboard showing summary of watchlist + trip plan activity
2. Cross-linking between deals and trip plans
3. Notification preferences integration
