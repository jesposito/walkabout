# Walkabout Implementation Plan

## Executive Summary

**Total Estimated Time:** 80-100 hours across 4 phases
**Monthly Cost:** ~$12-15 USD (Seats.aero + Claude API)

---

## Phase Overview

| Phase | Goal | Time | Status |
|-------|------|------|--------|
| **Phase 1a: Prove Ingestion** | Validate scraping stability | 15-20h | Not Started |
| **Phase 1b: Infrastructure** | Add production infrastructure | 15-20h | Not Started |
| **Phase 2: Intelligence** | AI + Awards + Analysis | 25-35h | Not Started |
| **Phase 3: Full Features** | Production + Extensibility | 25-30h | Not Started |

**Oracle Review Note**: Original Phase 1 split into 1a and 1b to validate scraping before adding complexity.

---

## Phase 1a: Prove Ingestion (15-20h)

**Goal:** Validate that scraping works reliably before investing in infrastructure.

**Oracle Review**: "MVP scope too large. Spend 30-40h on infrastructure and still don't have dependable prices."

### Success Criteria (MANDATORY before moving to 1b)
- [ ] 7 days of continuous scraping
- [ ] <10% failure rate
- [ ] At least 50 price points collected
- [ ] Deal notifications delivered

### Tasks

| ID | Task | Time | Dependencies | Status |
|----|------|------|--------------|--------|
| 1a.1 | Minimal Docker Setup | 2-3h | - | [ ] |
| 1a.2 | SearchDefinition + ScrapeHealth Models | 2-3h | 1a.1 | [x] |
| 1a.3 | Playwright Scraper with Failure Handling | 4-5h | 1a.1 | [x] |
| 1a.4 | Simple APScheduler (no Celery) | 2-3h | 1a.2, 1a.3 | [ ] |
| 1a.5 | ntfy Notifications (Deals + System) | 2-3h | 1a.4 | [ ] |
| 1a.6 | Barebones HTML Status Page | 2-3h | 1a.5 | [ ] |

### Task Details

#### 1a.1 Minimal Docker Setup (2-3h)

**Simplified services (no Celery/Redis yet):**
- PostgreSQL (plain, no TimescaleDB yet)
- FastAPI backend
- Playwright browser container
- ntfy

```yaml
# docker-compose.yml (simplified)
services:
  db:
    image: postgres:15
    # ...
  
  backend:
    build: ./backend
    depends_on: [db]
    # ...
  
  playwright:
    build: ./playwright
    # ...
  
  ntfy:
    image: binwiederhier/ntfy
    # ...
```

**Acceptance criteria:**
- [ ] `docker-compose up` starts 4 services
- [ ] Backend connects to Postgres
- [ ] Playwright container accessible

---

#### 1a.2 SearchDefinition + ScrapeHealth Models (2-3h) ✅

**Already implemented in this session:**
- `SearchDefinition` - fully specifies comparable price series
- `ScrapeHealth` - tracks scrape success/failure with circuit breaker
- `FlightPrice` - updated to use search_definition_id

**Files created:**
- `backend/app/models/search_definition.py`
- `backend/app/models/scrape_health.py`
- `backend/app/models/flight_price.py` (updated)

---

#### 1a.3 Playwright Scraper with Failure Handling (4-5h) ✅

**Already implemented in this session:**
- `ScrapeResult` dataclass with failure classification
- Failure reasons: captcha, timeout, layout_change, no_results, blocked
- Screenshot + HTML capture on failure
- Circuit breaker integration

**File updated:**
- `backend/app/scrapers/google_flights.py`

---

#### 1a.4 Simple APScheduler (2-3h)

**Use APScheduler instead of Celery for Phase 1a:**

```python
# backend/app/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job(CronTrigger(hour=6, minute=30))
async def morning_scrape():
    await scrape_all_active_definitions()

@scheduler.scheduled_job(CronTrigger(hour=18, minute=30))
async def evening_scrape():
    await scrape_all_active_definitions()
```

**Acceptance criteria:**
- [ ] Jobs run on schedule
- [ ] Failed jobs logged
- [ ] Manual trigger endpoint works

---

#### 1a.5 ntfy Notifications (2-3h)

**Notify on:**
1. **Deals** - price below threshold
2. **System failures** - consecutive scrape failures, stale data

```python
# backend/app/services/notification.py
async def send_system_alert(search_def: SearchDefinition, health: ScrapeHealth):
    """Alert when scraping is unhealthy."""
    if health.consecutive_failures >= 3:
        await ntfy.post(
            title=f"⚠️ Scraping Failing: {search_def.display_name}",
            message=f"{health.consecutive_failures} consecutive failures. "
                    f"Last error: {health.last_failure_reason}",
            priority="high",
            tags="warning"
        )
```

**Acceptance criteria:**
- [ ] Deal alerts work
- [ ] System failure alerts work
- [ ] Alert deduplication (don't spam)

---

#### 1a.6 Barebones HTML Status Page (2-3h)

**Simple Jinja2 template showing:**
- Active search definitions
- Last scrape time + status
- Health indicators (green/yellow/red)
- Manual "Scrape Now" button

**No React yet.** Just server-rendered HTML.

```python
# backend/app/api/dashboard.py
@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    definitions = db.query(SearchDefinition).filter(
        SearchDefinition.is_active == True
    ).all()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "definitions": definitions,
    })
```

**Acceptance criteria:**
- [ ] Shows all active monitors
- [ ] Health status visible at a glance
- [ ] Can manually trigger scrape

---

## Phase 1b: Add Infrastructure (15-20h)

**Goal:** Add production infrastructure after validating scraping stability.

**Prerequisites:** Phase 1a success criteria met.

### Tasks

| ID | Task | Time | Dependencies | Status |
|----|------|------|--------------|--------|
| 1b.1 | Migrate to TimescaleDB | 3-4h | Phase 1a | [ ] |
| 1b.2 | Add Celery + Redis | 4-5h | 1b.1 | [ ] |
| 1b.3 | Z-score Deal Detection | 3-4h | 1b.1 | [x] |
| 1b.4 | React Dashboard | 6-8h | 1b.1, 1b.3 | [ ] |

### Task Details

#### 1b.1 Migrate to TimescaleDB (3-4h)

**Convert Postgres to TimescaleDB:**

```sql
-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Convert flight_prices to hypertable
SELECT create_hypertable('flight_prices', 'scraped_at', 
    chunk_time_interval => INTERVAL '1 week',
    migrate_data => true);
```

**Acceptance criteria:**
- [ ] Hypertable created
- [ ] Existing data migrated
- [ ] Time-based queries faster

---

#### 1b.2 Add Celery + Redis (4-5h)

**Replace APScheduler with Celery for:**
- Better job monitoring
- Retry with backoff
- Distributed workers (future)

```python
# backend/celery_app/tasks/scrape_flights.py
@celery.task(bind=True, max_retries=3)
def scrape_search_definition(self, search_def_id: int):
    # ...
```

**Acceptance criteria:**
- [ ] Scheduled tasks work
- [ ] Retries on failure
- [ ] Flower monitoring (optional)

---

#### 1b.3 Z-score Deal Detection (3-4h) ✅

**Already implemented in this session:**
- `robust_z_score()` using median/MAD
- `is_absolute_new_low()` detection
- Updated `PriceAnalyzer` with both traditional and robust z-scores

**File updated:**
- `backend/app/services/price_analyzer.py`

---

#### 1b.4 React Dashboard (6-8h)

**Full React dashboard with:**
- Route cards with health status
- Price history charts (Recharts)
- Deal alerts timeline
- Mobile responsive

**Acceptance criteria:**
- [ ] Dashboard loads
- [ ] Charts display history
- [ ] Responsive design
- [ ] Error/loading states

---

## Phase 2: Intelligence Layer (25-35h)

**Goal:** AI-powered deal analysis, award flight tracking.

**Prerequisites:** Phase 1b complete.

### Tasks

| ID | Task | Time | Dependencies | Status |
|----|------|------|--------------|--------|
| 2.1 | Seats.aero API Integration | 5-6h | Phase 1b | [ ] |
| 2.2 | Miles Program Management | 4-5h | 2.1 | [ ] |
| 2.3 | Claude AI Integration | 6-8h | 2.1, 2.2 | [ ] |
| 2.4 | Advanced Price Analysis | 5-6h | Phase 1b | [ ] |
| 2.5 | Enhanced Dashboard | 6-8h | 2.1-2.4 | [ ] |

**Before starting Phase 2:**
- [ ] Verify Seats.aero covers AKL→HNL routes
- [ ] Verify Seats.aero supports Atmos/Airpoints

---

## Phase 3: Full Features (25-30h)

**Goal:** Production hardening, extensibility.

### Tasks

| ID | Task | Time | Dependencies | Status |
|----|------|------|--------------|--------|
| 3.1 | Multi-Destination Support | 4-5h | Phase 2 | [ ] |
| 3.2 | Resort Monitoring (Future) | 8-10h | 3.1 | [ ] |
| 3.3 | User Authentication | 5-6h | Phase 2 | [ ] |
| 3.4 | Production Hardening | 5-6h | All | [ ] |
| 3.5 | Extensibility Framework | 4-5h | 3.1 | [ ] |

---

## Security Posture

**Oracle Review**: "If exposed to internet without auth, it's an immediate risk."

### Phase 1 (Default Private)
- Bind all services to `127.0.0.1` only
- Access via Tailscale or SSH tunnel
- No authentication required (private network)

### Phase 3 (If Internet Exposed)
- Add reverse proxy (Traefik/Caddy)
- Basic auth or OAuth
- Rate limiting
- HTTPS required

**Do NOT expose to internet without Phase 3 auth implementation.**

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
│   │   ├── scheduler.py          # APScheduler (Phase 1a)
│   │   ├── models/
│   │   │   ├── search_definition.py  # NEW
│   │   │   ├── scrape_health.py      # NEW
│   │   │   ├── flight_price.py       # Updated
│   │   │   └── alert.py
│   │   ├── schemas/
│   │   ├── api/
│   │   ├── services/
│   │   │   ├── price_analyzer.py     # Updated with robust z-score
│   │   │   └── notification.py
│   │   └── scrapers/
│   │       └── google_flights.py     # Updated with failure handling
│   │
│   └── celery_app/               # Phase 1b
│       ├── celery.py
│       └── tasks/
│
├── frontend/                     # Phase 1b
│   └── ...
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

## Quick Start (Phase 1a)

```bash
# Clone and setup
git clone <repo> walkabout && cd walkabout
cp .env.example .env
# Edit .env with your settings

# Start minimal services
docker-compose up -d db playwright ntfy backend

# Run migrations
docker-compose exec backend alembic upgrade head

# Create first search definition
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.models import SearchDefinition, TripType, CabinClass
db = SessionLocal()
db.add(SearchDefinition(
    origin='AKL',
    destination='HNL',
    name='Auckland to Honolulu (Family)',
    trip_type=TripType.ROUND_TRIP,
    adults=2,
    children=2,
    cabin_class=CabinClass.ECONOMY,
    departure_days_min=60,
    departure_days_max=90,
    trip_duration_days_min=7,
    trip_duration_days_max=14,
))
db.commit()
"

# Access status page
open http://localhost:8000/
```

---

## Changelog

### 2026-01-21 - Oracle Review Implementation
- Split Phase 1 into 1a (prove ingestion) and 1b (infrastructure)
- Added `SearchDefinition` model for price comparability
- Added `ScrapeHealth` model with circuit breaker
- Added `ScrapeResult` with failure classification
- Updated scraper with failure handling + screenshots
- Added robust z-score (median/MAD) to price analyzer
- Added security posture documentation
