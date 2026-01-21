# Walkabout Phase 1a - Prove Ingestion

This directory contains Phase 1a implementation - the minimal viable system to prove scraping works reliably before adding infrastructure complexity.

## Oracle Review Implementation

This phase implements all the critical feedback from the Oracle review:

✅ **SearchDefinition model** - Fully specifies comparable price series  
✅ **ScrapeHealth model** - Tracks success/failure with circuit breaker  
✅ **ScrapeResult** - Failure classification (captcha/timeout/blocked/etc)  
✅ **Enhanced scraper** - Screenshot capture, proper error handling  
✅ **Robust z-score** - Uses median/MAD instead of mean/stddev  
✅ **Security posture** - Localhost-only binding  
✅ **Simplified stack** - PostgreSQL + APScheduler (no Celery/Redis yet)  

## Quick Start

```bash
# 1. Setup and start Phase 1a
./scripts/phase1a.sh

# 2. Access the status page
open http://localhost:8000/

# 3. Monitor logs
docker-compose -f docker-compose.phase1a.yml logs -f backend
```

## Architecture

```
Phase 1a Stack (Minimal):
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  FastAPI    │ Playwright  │ PostgreSQL  │    ntfy     │
│ +APScheduler│  (scraper)  │ (plain)     │(notifications)│
└─────────────┴─────────────┴─────────────┴─────────────┘

Missing from original plan (deferred to Phase 1b):
❌ TimescaleDB
❌ Celery + Redis  
❌ React frontend
```

## Success Criteria

Phase 1a must achieve these metrics before moving to Phase 1b:

- [ ] **7 days continuous operation** without manual intervention
- [ ] **<10% scrape failure rate** across all search definitions  
- [ ] **50+ price points collected** to validate deal detection
- [ ] **Deal notifications delivered** within 5 minutes of scrape
- [ ] **System failure alerts** working (stale data, consecutive failures)

## Key Files Added/Modified

### New Models (Oracle Review)
- `backend/app/models/search_definition.py` - Comparable price series specification
- `backend/app/models/scrape_health.py` - Health tracking with circuit breaker

### Enhanced Services  
- `backend/app/services/scraping_service.py` - Orchestrates entire pipeline
- `backend/app/services/price_analyzer.py` - Robust z-score + absolute new lows
- `backend/app/services/notification.py` - Deals + system alerts

### Phase 1a Infrastructure
- `backend/app/scheduler.py` - APScheduler (replaces Celery)
- `backend/app/api/status.py` - Status page API + manual controls
- `backend/app/templates/status.html` - Server-rendered dashboard
- `docker-compose.phase1a.yml` - Simplified Docker stack
- `scripts/phase1a.sh` - Setup automation

## Using the System

### Status Page
Visit `http://localhost:8000/` to see:
- System health (scheduler, ntfy, database)
- Search definition health with metrics
- Manual scrape triggers
- Recent price counts

### Manual Operations
```bash
# Trigger manual scrape for specific search definition
curl -X POST http://localhost:8000/api/scrape/manual/1

# Trigger scrape for all active definitions  
curl -X POST http://localhost:8000/api/scrape/manual/all

# Test notifications
curl -X POST http://localhost:8000/api/notifications/test

# View recent prices for a search definition
curl http://localhost:8000/search/1/prices
```

### Notifications
Subscribe to notifications by visiting: `http://localhost:8080/walkabout-deals`

You'll receive:
- **Deal alerts** when prices drop below z-score threshold or hit new lows
- **System alerts** for consecutive failures or stale data

## Configuration

Edit `.env` to configure:

```env
# Database (required)
DB_PASSWORD=your_secure_password

# Notifications (required)  
NTFY_TOPIC=walkabout-deals

# Optional for Phase 1a
SEATS_AERO_API_KEY=your_key  # For Phase 2
ANTHROPIC_API_KEY=your_key   # For Phase 2  
```

## Monitoring

### Logs
```bash
# All services
docker-compose -f docker-compose.phase1a.yml logs -f

# Just backend (most important)
docker-compose -f docker-compose.phase1a.yml logs -f backend

# APScheduler jobs
docker-compose -f docker-compose.phase1a.yml logs -f backend | grep "scrape"
```

### Health Endpoints
```bash
# Overall health
curl http://localhost:8000/api/status/health

# Detailed scheduler status  
curl http://localhost:8000/api/status/scheduler

# Database connectivity
curl http://localhost:8000/ping
```

## Common Issues

### Scraper Failures
- Check screenshots in `./data/screenshots/` for captcha/layout changes
- Review HTML snapshots in `./data/html_snapshots/`
- Adjust user agents or delays in `google_flights.py`

### Notifications Not Working
- Verify ntfy container: `docker-compose -f docker-compose.phase1a.yml logs ntfy`
- Test connectivity: `curl http://localhost:8080/v1/health`
- Check topic subscription at `http://localhost:8080/walkabout-deals`

### Database Issues
- Verify PostgreSQL: `docker-compose -f docker-compose.phase1a.yml logs db`
- Run migrations manually: `docker-compose -f docker-compose.phase1a.yml exec backend alembic upgrade head`

## Next Steps

Once Phase 1a success criteria are met:

1. **Analyze metrics** - scrape success rate, deal detection accuracy
2. **Document learnings** - what worked, what needed adjustment  
3. **Plan Phase 1b** - add TimescaleDB, Celery, React dashboard
4. **Migrate gradually** - preserve working Phase 1a as fallback

## Phase 1a vs Original Plan

| Component | Original Plan | Phase 1a Reality | Phase 1b |
|-----------|--------------|------------------|----------|
| Database | TimescaleDB | Plain PostgreSQL | TimescaleDB |
| Scheduling | Celery + Redis | APScheduler | Celery + Redis |
| Frontend | React | Server HTML | React |
| Deal Detection | Basic z-score | Robust z-score + new lows | Enhanced |
| Health Tracking | None | Circuit breaker + alerts | Same |
| Failure Handling | Basic | Screenshot + classification | Same |

**Oracle's wisdom**: "Tighten MVP around reliable ingestion + alerts + minimal UI before adding complexity."