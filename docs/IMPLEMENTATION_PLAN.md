# Walkabout Implementation Plan

## Executive Summary

**Total Estimated Time:** 80-100 hours across 3 phases
**Monthly Cost:** ~$12-15 USD (Seats.aero + Claude API)

---

## Phase Overview

| Phase | Goal | Time | Status |
|-------|------|------|--------|
| **Phase 1: MVP** | Scrape, store, alert | 30-40h | Not Started |
| **Phase 2: Intelligence** | AI + Awards + Analysis | 25-35h | Not Started |
| **Phase 3: Full Features** | Production + Extensibility | 25-30h | Not Started |

---

## Phase 1: MVP (Get Something Working)

**Goal:** Working system that scrapes Google Flights, stores prices, and sends ntfy notifications when deals are detected.

### Tasks

| ID | Task | Time | Dependencies | Status |
|----|------|------|--------------|--------|
| 1.1 | Docker Infrastructure Setup | 4-5h | - | [ ] |
| 1.2 | Database Models & Migrations | 3-4h | 1.1 | [ ] |
| 1.3 | Google Flights Playwright Scraper | 8-10h | 1.1 | [ ] |
| 1.4 | Celery Task Setup | 4-5h | 1.2, 1.3 | [ ] |
| 1.5 | Basic Deal Detection (Z-score) | 4-5h | 1.2, 1.4 | [ ] |
| 1.6 | ntfy Notification Integration | 3-4h | 1.1, 1.5 | [ ] |
| 1.7 | Basic FastAPI Endpoints | 4-5h | 1.2 | [ ] |
| 1.8 | Minimal React Dashboard | 6-8h | 1.7 | [ ] |

### Task Details

#### 1.1 Docker Infrastructure Setup (4-5h)

**Files to create:**
```
docker-compose.yml
.env.example
backend/Dockerfile
playwright/Dockerfile
```

**Services:**
- PostgreSQL + TimescaleDB
- Redis
- FastAPI backend
- Celery worker + beat
- ntfy
- Playwright browser container

**Acceptance criteria:**
- [ ] `docker-compose up` starts all services
- [ ] All containers show healthy
- [ ] Data persists across restarts

---

#### 1.2 Database Models & Migrations (3-4h)

**Files to create:**
```
backend/app/database.py
backend/app/models/base.py
backend/app/models/flight_price.py
backend/app/models/route.py
backend/app/models/alert.py
backend/alembic.ini
backend/alembic/env.py
backend/alembic/versions/001_initial.py
```

**Core models:**

```python
class FlightPrice(Base):
    """TimescaleDB hypertable for price time-series"""
    id: BigInteger
    route_id: Integer (FK)
    scraped_at: DateTime  # Partition column
    departure_date: Date
    return_date: Date
    price_nzd: Numeric(10,2)
    airline: String
    stops: Integer
    cabin_class: String
    raw_data: JSONB

class Route(Base):
    """Monitored flight routes"""
    id: Integer
    origin: String(3)  # IATA code
    destination: String(3)
    name: String
    is_active: Boolean
    scrape_frequency_hours: Integer
```

**Migration SQL:**
```sql
SELECT create_hypertable('flight_prices', 'scraped_at', 
    chunk_time_interval => INTERVAL '1 week');
```

**Acceptance criteria:**
- [ ] Migrations run without errors
- [ ] Hypertable created for flight_prices
- [ ] Can insert and query prices

---

#### 1.3 Google Flights Playwright Scraper (8-10h)

**Files to create:**
```
backend/app/scrapers/base.py
backend/app/scrapers/google_flights.py
playwright/Dockerfile
```

**Key implementation:**
```python
class GoogleFlightsScraper:
    """
    URL pattern:
    https://www.google.com/travel/flights?q=flights%20from%20AKL%20to%20HNL...
    
    Anti-detection:
    - playwright-stealth for fingerprint masking
    - Random delays 2-5 seconds
    - Limit to 2x daily per route
    - Rotate user agents
    """
    
    async def scrape_route(
        self, 
        origin: str, 
        destination: str,
        departure_date: date,
        return_date: date,
        passengers: int = 4
    ) -> list[FlightResult]:
        pass
```

**Acceptance criteria:**
- [ ] Returns valid prices for AKL→HNL
- [ ] Handles errors gracefully
- [ ] Works inside Docker container
- [ ] Not blocked after 10 consecutive scrapes

---

#### 1.4 Celery Task Setup (4-5h)

**Files to create:**
```
backend/celery_app/celery.py
backend/celery_app/tasks/__init__.py
backend/celery_app/tasks/scrape_flights.py
```

**Schedule:**
```python
app.conf.beat_schedule = {
    'scrape-morning': {
        'task': 'scrape_all_routes',
        'schedule': crontab(hour=6, minute=30),  # 6:30 AM NZT
    },
    'scrape-evening': {
        'task': 'scrape_all_routes',
        'schedule': crontab(hour=18, minute=30),  # 6:30 PM NZT
    },
}
```

**Acceptance criteria:**
- [ ] Tasks execute on schedule
- [ ] Failed tasks retry with backoff
- [ ] Results logged

---

#### 1.5 Basic Deal Detection (4-5h)

**Files to create:**
```
backend/app/services/price_analyzer.py
```

**Detection logic:**
```python
class PriceAnalyzer:
    """
    A price is a "deal" if:
    1. Z-score < -1.5 (1.5 std devs below mean)
    2. At least 10 historical prices exist
    3. Price drop > $100 from last scrape (optional)
    """
    
    def analyze_price(self, price: FlightPrice) -> DealAnalysis:
        history = self.get_price_history(route_id, date_window_days=14)
        if len(history) < 10:
            return DealAnalysis(is_deal=False, reason="Insufficient history")
        
        mean = statistics.mean(history)
        stdev = statistics.stdev(history)
        z_score = (price.price_nzd - mean) / stdev
        
        return DealAnalysis(
            is_deal=(z_score < -1.5),
            z_score=z_score,
            mean_price=mean,
            percentile=self.calculate_percentile(price.price_nzd, history)
        )
```

**Acceptance criteria:**
- [ ] Z-score calculation verified
- [ ] Unit tests pass
- [ ] Deals detected when price significantly below average

---

#### 1.6 ntfy Notification Integration (3-4h)

**Files to create:**
```
backend/app/services/notification.py
```

**Implementation:**
```python
class NtfyNotifier:
    async def send_deal_alert(self, deal: DealAnalysis, price: FlightPrice):
        message = f"""
🎉 Flight Deal Alert!
{route.name}
{price.departure_date} - {price.return_date}
💰 ${price.price_nzd:.0f} NZD
📉 {abs(deal.price_vs_mean):.0f} below average
"""
        await httpx.post(
            f"{self.base_url}/walkabout-deals",
            content=message,
            headers={
                "Title": f"Flight Deal: ${price.price_nzd:.0f}",
                "Priority": "high" if deal.z_score < -2 else "default",
                "Tags": "airplane,moneybag",
            }
        )
```

**Acceptance criteria:**
- [ ] Notifications arrive on phone
- [ ] Priority levels work
- [ ] All deal info included

---

#### 1.7 Basic FastAPI Endpoints (4-5h)

**Files to create:**
```
backend/app/main.py
backend/app/api/routes.py
backend/app/api/prices.py
backend/app/api/health.py
backend/app/schemas/
```

**Endpoints:**
```
GET  /api/routes                    # List routes
POST /api/routes                    # Add route
GET  /api/prices/{route_id}         # Price history
GET  /api/prices/{route_id}/latest  # Latest prices
GET  /api/prices/{route_id}/stats   # Statistics
GET  /api/health                    # Health check
POST /api/scrape/trigger            # Manual scrape
```

**Acceptance criteria:**
- [ ] OpenAPI docs at /docs
- [ ] CRUD operations work
- [ ] Error handling proper

---

#### 1.8 Minimal React Dashboard (6-8h)

**Files to create:**
```
frontend/Dockerfile
frontend/package.json
frontend/src/App.tsx
frontend/src/pages/Dashboard.tsx
frontend/src/components/PriceChart.tsx
frontend/src/components/RouteCard.tsx
```

**Features:**
- List monitored routes with latest prices
- Line chart of price history (30 days)
- Deal score indicator
- Last scrape status
- Manual "Scrape Now" button

**Tech stack:**
- Vite
- Tailwind CSS
- Recharts
- React Query

**Acceptance criteria:**
- [ ] Dashboard loads and shows routes
- [ ] Price chart displays history
- [ ] Responsive for mobile
- [ ] Loading/error states handled

---

### Phase 1 Completion Criteria

| Requirement | Met |
|-------------|-----|
| System runs 7 days unattended | [ ] |
| Scrapes 2x daily | [ ] |
| At least 100 price points collected | [ ] |
| Deal notifications delivered <5 min | [ ] |
| Dashboard shows price charts | [ ] |

---

## Phase 2: Intelligence Layer

**Goal:** AI-powered deal analysis, award flight tracking, and advanced price analytics.

### Tasks

| ID | Task | Time | Dependencies | Status |
|----|------|------|--------------|--------|
| 2.1 | Seats.aero API Integration | 5-6h | Phase 1 | [ ] |
| 2.2 | Miles Program Management | 4-5h | 2.1 | [ ] |
| 2.3 | Claude AI Integration | 6-8h | 2.1, 2.2 | [ ] |
| 2.4 | Advanced Price Analysis | 5-6h | Phase 1 | [ ] |
| 2.5 | Enhanced Dashboard | 6-8h | 2.1-2.4 | [ ] |

### Task Details

#### 2.1 Seats.aero API Integration (5-6h)

**Files to create:**
```
backend/app/services/seats_aero.py
backend/app/models/award_availability.py
backend/celery_app/tasks/fetch_awards.py
```

**Award availability model:**
```python
class AwardAvailability(Base):
    id: BigInteger
    route_id: Integer (FK)
    fetched_at: DateTime
    departure_date: Date
    program: String  # "Atmos", "Airpoints"
    cabin: String
    seats_available: Integer
    miles_cost: Integer
    taxes_usd: Numeric
```

**Acceptance criteria:**
- [ ] Auth with Seats.aero API
- [ ] Fetch NZ route availability
- [ ] Store in database
- [ ] Handle rate limits

---

#### 2.2 Miles Program Management (4-5h)

**Files to create:**
```
backend/app/models/miles_program.py
backend/app/api/miles.py
frontend/src/components/MilesTracker.tsx
```

**Features:**
- Track multiple programs (Atmos, Airpoints)
- Manual balance entry
- Value per point calculation
- Cash vs miles comparison

**Acceptance criteria:**
- [ ] Track balances
- [ ] Calculate redemption value
- [ ] Show on dashboard

---

#### 2.3 Claude AI Integration (6-8h)

**Files to create:**
```
backend/app/services/ai_advisor.py
backend/celery_app/tasks/analyze_deals.py
```

**AI features:**
```python
class ClaudeAdvisor:
    async def analyze_deal(self, deal, context) -> str:
        """
        Only called when z_score < -1.5 (cost control)
        
        Returns:
        - Is this a good deal? (historical context)
        - Should we book now or wait?
        - Cash vs miles recommendation
        - Timing considerations
        """
    
    async def generate_weekly_digest(self, week_data) -> str:
        """Weekly summary of opportunities"""
```

**Cost controls:**
- Only call on threshold deals
- Cache 24 hours
- Batch multiple deals
- Target: <$5/month

**Acceptance criteria:**
- [ ] Useful contextual advice
- [ ] Responses cached
- [ ] Cost <$5/month
- [ ] Graceful API fallback

---

#### 2.4 Advanced Price Analysis (5-6h)

**Files to enhance:**
```
backend/app/services/price_analyzer.py
backend/alembic/versions/002_continuous_aggregates.py
```

**Features:**
- Seasonal baselines by travel month
- TimescaleDB continuous aggregates
- Trend prediction (rising/falling)
- Multi-factor anomaly detection

**Continuous aggregate:**
```sql
CREATE MATERIALIZED VIEW price_monthly_stats
WITH (timescaledb.continuous) AS
SELECT
    route_id,
    time_bucket('1 month', scraped_at) AS month,
    EXTRACT(MONTH FROM departure_date) AS travel_month,
    AVG(price_nzd), STDDEV(price_nzd), MIN(price_nzd), COUNT(*)
FROM flight_prices
GROUP BY ...
```

**Acceptance criteria:**
- [ ] Seasonal baselines work
- [ ] Aggregates auto-refresh
- [ ] Trend indicators shown

---

#### 2.5 Enhanced Dashboard (6-8h)

**Files to enhance:**
```
frontend/src/pages/Dashboard.tsx
frontend/src/components/DealCard.tsx
frontend/src/components/MilesComparison.tsx
```

**New features:**
- Award + cash prices side by side
- Miles vs cash calculator
- AI advice display
- Seasonal context indicators
- Price trend arrows

**Acceptance criteria:**
- [ ] Both options displayed
- [ ] "Best option" highlighted
- [ ] AI advice shown
- [ ] Mobile friendly

---

### Phase 2 Completion Criteria

| Requirement | Met |
|-------------|-----|
| Award availability integrated | [ ] |
| Miles balances tracked | [ ] |
| AI advice on deals | [ ] |
| Cash vs miles comparison | [ ] |
| Cost < $15/month total | [ ] |

---

## Phase 3: Full Features

**Goal:** Production hardening, extensibility, and additional destinations.

### Tasks

| ID | Task | Time | Dependencies | Status |
|----|------|------|--------------|--------|
| 3.1 | Multi-Destination Support | 4-5h | Phase 2 | [ ] |
| 3.2 | Resort Monitoring (Future) | 8-10h | 3.1 | [ ] |
| 3.3 | User Authentication | 5-6h | Phase 2 | [ ] |
| 3.4 | Production Hardening | 5-6h | All | [ ] |
| 3.5 | Extensibility Framework | 4-5h | 3.1 | [ ] |

---

## Project Structure

```
walkabout/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/
│   │
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── services/
│   │   └── scrapers/
│   │
│   └── celery_app/
│       ├── celery.py
│       └── tasks/
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   ├── components/
│   │   └── hooks/
│
├── playwright/
│   └── Dockerfile
│
└── scripts/
    ├── init-db.sh
    └── backup.sh
```

---

## Cost Summary

| Service | Monthly Cost |
|---------|--------------|
| Seats.aero Pro | ~$10 USD |
| Claude API | ~$2-5 USD |
| Self-hosted | $0 |
| **Total** | **~$12-15 USD** |

---

## Success Metrics

| Phase | Milestone | Target |
|-------|-----------|--------|
| 1 | System runs 7 days | Week 4 |
| 1 | 100+ price points | Week 4 |
| 2 | Award data integrated | Week 8 |
| 2 | AI cost <$5/mo | Week 8 |
| 3 | 3+ destinations | Week 12 |
| 3 | Full backup/restore tested | Week 12 |

---

## Quick Start (Development)

```bash
# Clone and setup
git clone <repo> walkabout && cd walkabout
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Seed initial route
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import Route
db = SessionLocal()
db.add(Route(origin='AKL', destination='HNL', name='Auckland to Honolulu'))
db.commit()
"

# Access
# API: http://localhost:8000/docs
# Frontend: http://localhost:3000
# ntfy: http://localhost:8080
```
