# Oracle Review - Critical Feedback

*Strategic review conducted 2026-01-21*

---

## Executive Summary

> "Your overall direction is sound, but the plan underestimates scraping fragility and overbuilds MVP before proving data acquisition stability."

**Key insight**: Tighten MVP around "reliable ingestion + alerts + minimal UI" before adding complexity.

---

## Critical Issues (MUST FIX)

### 1. Scraping is Single Point of Failure

**Problem**: Google Flights is actively hostile to automation. "Stealth mode" is not a plan.

**Missing**: First-class scrape health model:
- Success/failure metrics per route
- Failure reason classification (timeout/captcha/layout/no-results)
- Last-good-data timestamp per route
- Alert on stale data (no successful scrape for X hours)
- Screenshot + HTML snapshot on failure for debugging

**Action**: Add `ScrapeHealth` model and stale-data alerting before anything else.

---

### 2. MVP Scope Too Large

**Problem**: TimescaleDB + Celery + Redis + Playwright + React is a lot of moving parts before validating "does scraping even work reliably?"

**Risk**: Spend 30-40h on infrastructure and still don't have dependable prices.

**Action**: Re-scope MVP:
1. **Phase 1a (Prove Ingestion)**: Playwright scraper → plain Postgres → ntfy alerts → barebones HTML UI
2. **Phase 1b (Add Infrastructure)**: Add TimescaleDB, Celery, React only after stable writes

**Consider**: Defer Celery/Redis initially. A single cron/APScheduler can run 2-6 jobs/day safely.

---

### 3. Data Model Ambiguity

**Problem**: Flight price is not a single scalar. Without persisting full query parameters, history becomes non-comparable.

**Missing dimensions**:
- Route (origin, destination)
- Dates (departure, return)
- Trip type (round-trip, one-way)
- Passengers (2 adults + 2 children vs 4 adults)
- Cabin class
- Bags included
- Stops (any, nonstop, max 1)
- Airline filters
- Currency
- Point of sale/locale

**Action**: Create `SearchDefinition` (or `Monitor`) entity that fully specifies what a price series means. Any change = new version.

---

### 4. Z-Score Assumptions Can Misfire

**Problem**: Flight pricing is non-stationary and discontinuous. Mean/stddev can be skewed by spikes.

**Missing**:
- Outlier handling (winsorize/clamp extremes)
- Minimum sample quality checks
- "Structural break" detection (reset baseline when route/schedule changes)

**Action**: Add guardrails:
- Use median + MAD (median absolute deviation) as alternative to mean + stddev
- "New absolute low" alert independent of z-score
- Require minimum N valid samples before calculating z-score

---

### 5. No Security Boundary

**Problem**: If exposed to internet without auth, it's an immediate risk.

**Missing**:
- "Default private" posture (VPN-only or reverse proxy auth)
- Secret management
- Least-privilege DB credentials

**Action**: MVP should be localhost/Tailscale only. Add auth before any internet exposure.

---

### 6. Seats.aero Coverage Uncertainty

**Problem**: May not align with Air NZ-centric redemption realities.

**Action**: Before building Phase 2, VERIFY:
- Does Seats.aero cover AKL→HNL routes?
- Does it support Atmos Rewards and Airpoints redemption search?
- What's the data freshness?

---

## Recommendations (SHOULD DO)

### 1. Explicit Failure Handling

```python
class ScrapeResult:
    status: Literal["success", "captcha", "timeout", "layout_change", "no_results", "blocked"]
    prices: list[FlightPrice] | None
    screenshot_path: str | None  # On failure
    html_snapshot_path: str | None  # On failure
    error_message: str | None

class ScrapeHealth:
    monitor_id: int
    last_success_at: datetime | None
    last_failure_at: datetime | None
    consecutive_failures: int
    failure_reason: str | None
```

### 2. Adaptive Scrape Frequency

- Baseline: 2x daily
- Increase to 4-6x when:
  - Travel dates within 2 months
  - Z-score approaching threshold (-1.0 to -1.5)
  - Known sale periods (Black Friday, etc.)

### 3. Robust Detection Primitives

```python
def robust_z_score(current_price: float, history: list[float]) -> float:
    """Use median + MAD instead of mean + stddev for robustness"""
    median = statistics.median(history)
    mad = statistics.median([abs(x - median) for x in history])
    if mad == 0:
        mad = 1.0
    return (current_price - median) / (mad * 1.4826)  # Scale factor for normal dist
```

### 4. AI Response Caching

Cache by `(search_definition_id, deal_event_id)` not just time-based 24h cache.

### 5. Operational Baseline from Day 1

- Automated DB backups (pg_dump daily to Unraid share)
- Container healthchecks + restart policies
- `/health` endpoint showing last scrape time per monitor
- ntfy alert on SYSTEM failures, not just deals
- Retention policy for old price data (keep 2 years, compress older)

---

## Nice-to-Haves

1. **Price distribution bands**: Track rolling P10/P25/P50 per monitor (more interpretable than z-score)
2. **Itinerary fingerprints**: Store airline/flight numbers/stops when extractable
3. **Monitor builder UI**: Simple form to create search definitions
4. **Local LLM option**: Design for Claude now, but swap later if needed

---

## Validation (What's Good)

- **Phased delivery** is pragmatic
- **"Rules detect, AI explains"** keeps costs low
- **TimescaleDB** is right fit for time-series (after stable ingestion)
- **ntfy** is excellent self-hosted notification choice
- **Skipping geo-arbitrage** is correct for NZ→Hawaii

---

## Revised Phase 1 Structure

### Phase 1a: Prove Ingestion (15-20h)
- [ ] Playwright scraper with failure handling
- [ ] Plain PostgreSQL (no TimescaleDB yet)
- [ ] `SearchDefinition` and `ScrapeHealth` models
- [ ] Simple cron scheduler (no Celery)
- [ ] ntfy alerts for deals AND system failures
- [ ] Barebones HTML status page (no React)

**Success criteria**: 7 days of reliable scraping with <10% failure rate

### Phase 1b: Add Infrastructure (15-20h)
- [ ] Migrate to TimescaleDB hypertables
- [ ] Add Celery + Redis for job management
- [ ] React dashboard with charts
- [ ] Z-score deal detection with guardrails

**Success criteria**: 100+ comparable price points, deal notifications working

---

## Action Items

| Priority | Item | Status |
|----------|------|--------|
| P0 | Add `SearchDefinition` model | [x] ✅ 2026-01-21 |
| P0 | Add `ScrapeHealth` model with stale-data alerts | [x] ✅ 2026-01-21 |
| P0 | Implement failure classification + screenshots | [x] ✅ 2026-01-21 |
| P0 | Add security posture (localhost/Tailscale only) | [x] ✅ 2026-01-21 (in IMPLEMENTATION_PLAN.md) |
| P1 | Split Phase 1 into 1a/1b | [x] ✅ 2026-01-21 |
| P1 | Add robust z-score (median/MAD variant) | [x] ✅ 2026-01-21 |
| P1 | Verify Seats.aero NZ route coverage | [ ] (Before Phase 2) |
| P2 | Add adaptive scrape frequency | [ ] |
| P2 | Add operational baseline (backups, healthchecks) | [ ] |
