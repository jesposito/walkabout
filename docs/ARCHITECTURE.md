# Walkabout Architecture

## Overview

Self-hosted travel deal monitor with AI-enhanced analysis. Tracks flight prices (cash + award), resort deals, and provides intelligent recommendations.

---

## Data Acquisition Strategy

### Tier 1: Self-Scraping (Free, More Work)

**Google Flights via Playwright**
- Working scrapers exist: `harsh-vardhhan/google-flight-scraping-playwright`, `techwithtim/BDAIScraperAgent`
- Challenges: Rate limiting, occasional CAPTCHAs, dynamic content
- Mitigation: Headless browser with stealth mode, random delays, residential proxies if needed
- **Verdict: Viable for personal daily use (1-2 searches/day per route)**

**Airline Websites (Hawaiian, Air NZ)**
- No public scrapers available
- Heavy bot protection expected
- **Verdict: Not recommended - use Google Flights as single source**

### Tier 2: Paid APIs (Reliable, Costs Money)

| Service | Use Case | Cost | When to Use |
|---------|----------|------|-------------|
| SerpAPI | Google Flights backup | $50/mo | If scraping breaks |
| Seats.aero | Award availability | $10/mo | Essential for miles tracking |

### Recommended Approach: Hybrid

1. **Primary**: Self-scrape Google Flights with Playwright
2. **Fallback**: SerpAPI if scraping fails repeatedly
3. **Award flights**: Seats.aero Pro API (no good self-scrape option)

---

## Geo-Arbitrage: Reality Check

### Research Findings

**The hype is overblown.** Real-world testing shows:
- Flight prices vary **5-15%** by region, not 50%+
- USA Today (Jan 2026): "minimal savings" on flights
- PC Magazine: tested 12 countries, found "minimal differences"

### When It DOES Matter
- Booking flights in local currency during favorable exchange rates
- Some routes (especially to/from developing countries)
- Hotel bookings show more variation than flights

### Practical Implementation

**Option 1: Single Gluetun with Rotation (Recommended)**
```yaml
# docker-compose.yml excerpt
gluetun:
  environment:
    - VPN_SERVICE_PROVIDER=mullvad
    - SERVER_COUNTRIES=New Zealand,United States,United Kingdom,Japan
```
- Use `ingestbot/randomizer` to rotate countries on schedule
- One container, one VPN subscription
- Check 3-4 key markets

**Option 2: Residential Proxy (If Needed)**
- Bright Data: $4-8/GB with geo-targeting
- Only if geo-arbitrage proves valuable for your routes
- Start without it, add later if data shows benefit

**Recommendation**: Start with single-country scraping. Add geo-rotation only after you have baseline data proving it matters for NZ→Hawaii routes.

---

## Notification System

### Comparison

| Service | Self-Host | Docker | Mobile App | Rich Notifications | API Simplicity |
|---------|-----------|--------|------------|-------------------|----------------|
| **ntfy** | Yes | Yes | Yes (Android/iOS) | Yes (actions, images) | Excellent (curl) |
| Gotify | Yes | Yes | Android only | Basic | Good |
| Apprise | Library | N/A | Via other services | Via other services | Good |
| Pushover | No | N/A | Yes | Yes | Good |

### Recommendation: **ntfy**

- Fully self-hostable on Unraid
- Dead-simple API: `curl -d "Flight deal!" ntfy.sh/walkabout`
- Mobile apps for both platforms
- Action buttons ("View Deal", "Dismiss")
- Free tier on ntfy.sh works while you set up self-hosted

```bash
# Example notification
curl -H "Title: AKL→HNL Price Drop" \
     -H "Priority: high" \
     -H "Tags: airplane,moneybag" \
     -d "Round-trip for 4: $4,200 NZD (18-month low!)" \
     ntfy.sh/your-topic
```

---

## AI Integration Strategy

### Philosophy
> "Rules detect, AI explains and advises"

LLMs are expensive and slow. Use them strategically:

| Task | Use AI? | Why |
|------|---------|-----|
| Detect price drop | No | Simple math |
| Rank deals by price | No | Sorting |
| Explain WHY a deal is good | **Yes** | Context + natural language |
| "Should we book?" advice | **Yes** | Reasoning over constraints |
| Trip planning strategy | **Yes** | Complex trade-offs |

### Data Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Scrape → Normalize → Compute Features → Gate → AI Enrich → Notify
│           (free)      (free)           (free)  (paid)     (free)
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐            │
│  │ Raw prices  │→ │ Z-scores     │→ │ Threshold   │            │
│  │ from Google │  │ Seasonality  │  │ crossed?    │            │
│  │ Flights     │  │ Rolling avg  │  │             │            │
│  └─────────────┘  │ Volatility   │  │ Yes → AI    │            │
│                   └──────────────┘  │ No → Skip   │            │
│                                     └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### When to Call Claude API

**DO call Claude when:**
- Deal crosses significance threshold (new low, big drop, award availability)
- User asks "Should we book?"
- Daily/weekly digest generation
- Trip planning session

**DON'T call Claude when:**
- Every scrape (wasteful)
- Simple price sorting
- Recomputing unchanged data (cache instead)

### AI Features by Priority

| Priority | Feature | Value | Cost |
|----------|---------|-------|------|
| 1 | **Deal explanations** ("This is the lowest price in 8 months, during shoulder season") | Very High | Low (gated) |
| 2 | **"Should we book?" assistant** with family constraints | Very High | Medium (on-demand) |
| 3 | **Miles strategy advisor** ("Use 180k Atmos points now, or wait?") | High | Medium |
| 4 | **Weekly digest summary** | Medium | Low (batched) |
| 5 | **Pattern insights** ("Prices for this route usually drop in March") | Medium | Low (monthly) |

### Prompt Architecture

```json
// Input to Claude (structured, compact)
{
  "route": {"origin": "AKL", "dest": "HNL", "dates": "2026-04-15/2026-04-25"},
  "current_price": {"cash_nzd": 4200, "per_person": 1050},
  "metrics": {
    "vs_90d_avg": -18,
    "vs_365d_low": +2,
    "z_score": -2.1,
    "seasonality": "shoulder"
  },
  "family_profile": {
    "travelers": 4,
    "school_holidays": ["2026-04-11", "2026-04-26"],
    "max_stops": 1,
    "miles_balance": {"atmos": 185000, "airpoints": 450}
  }
}

// Output from Claude (strict JSON)
{
  "headline": "Strong deal for school holiday timing",
  "why_good": [
    "18% below 90-day average",
    "Only $50/person above all-time low",
    "Dates align with school holidays"
  ],
  "confidence": "high",
  "recommendation": "book_soon",
  "caveats": [
    "Price volatility is moderate - could drop another 5-10%",
    "April is popular - availability may decrease"
  ],
  "miles_comparison": "Cash is better value than 180k Atmos points (0.58 cpp vs typical 1.2 cpp)"
}
```

### Cost Estimate

| Usage | Calls/Month | Tokens | Cost |
|-------|-------------|--------|------|
| Deal alerts (5/day, 20% hit AI) | ~30 | ~50k | ~$1 |
| Weekly digests | 4 | ~20k | ~$0.40 |
| User queries | ~20 | ~40k | ~$0.80 |
| **Total** | | | **~$2-5/mo** |

---

## Historical Analysis That Actually Works

### Proven Patterns (from research)

1. **Day of week to FLY** (not book): Tue/Wed 15% cheaper than Fri/Sun
2. **Booking window**: 3-6 weeks before domestic, 2-3 months before international
3. **Seasonality**: Track YOUR route, not generic advice
4. **Volatility windows**: Prices most volatile 2-4 weeks before departure

### Data Requirements

| Analysis Type | Data Needed | Time to Useful |
|---------------|-------------|----------------|
| Basic trends | 30 days | Immediate |
| Seasonality | 12 months | 6-12 months |
| Reliable predictions | 2+ years | Long-term |

### Implementation

```sql
-- Seasonality baseline (after 12 months of data)
SELECT 
  EXTRACT(MONTH FROM departure_date) as month,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_nzd) as median_price,
  PERCENTILE_CONT(0.1) WITHIN GROUP (ORDER BY price_nzd) as good_price
FROM flight_prices
WHERE route = 'AKL-HNL'
GROUP BY month;

-- Z-score for current price
WITH stats AS (
  SELECT AVG(price_nzd) as mean, STDDEV(price_nzd) as stddev
  FROM flight_prices
  WHERE route = 'AKL-HNL' 
    AND scraped_at > NOW() - INTERVAL '90 days'
)
SELECT (current_price - mean) / stddev as z_score FROM stats;
```

### Alert Thresholds

| Trigger | Condition | Priority |
|---------|-----------|----------|
| New all-time low | price < MIN(365d) | Critical |
| Significant drop | z_score < -2.0 | High |
| Below good threshold | price < P10 (90d) | Medium |
| Award seats available | 4+ seats for family | High |

---

## Miles Programs Support

### Initial Support
- **Atmos Rewards** (Alaska + Hawaiian) - Primary
- **Air NZ Airpoints** - Secondary

### Data Model (Extensible)

```python
class MilesProgram:
    id: str
    name: str  # "Atmos Rewards", "Airpoints"
    user_balance: int
    typical_cpp: float  # cents per point (for value comparison)
    notes: str  # quirks, transfer partners, etc.

class AwardPrice:
    route_id: str
    program_id: str
    miles_required: int
    taxes_fees_nzd: float
    cabin: str
    availability: int  # seats available
```

### Miles Value Calculation

```python
def should_use_miles(cash_price_nzd, miles_required, taxes_nzd, typical_cpp=1.2):
    """
    Compare cash vs miles value.
    typical_cpp: typical cents per point value (Atmos ~1.2cpp)
    """
    effective_cash_price = cash_price_nzd - taxes_nzd
    implied_cpp = (effective_cash_price * 100) / miles_required
    
    return {
        "implied_cpp": implied_cpp,
        "vs_typical": implied_cpp / typical_cpp,
        "recommendation": "use_miles" if implied_cpp > typical_cpp else "pay_cash"
    }
```

---

## Tech Stack (Final)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Backend** | Python + FastAPI | Async, Playwright support, good AI libs |
| **Frontend** | React + Tailwind | Modern, responsive |
| **Database** | PostgreSQL + TimescaleDB | Time-series optimized |
| **Scraping** | Playwright | Handles dynamic content |
| **Job Queue** | Celery + Redis | Reliable scheduling |
| **AI** | Claude API (Anthropic) | Best reasoning |
| **Notifications** | ntfy (self-hosted) | Simple, self-hosted |
| **VPN** | Gluetun (optional) | Geo-rotation if needed |
| **Container** | Docker Compose | Unraid-ready |

---

## File Structure

```
walkabout/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── models/              # SQLAlchemy models
│   │   ├── scrapers/
│   │   │   ├── google_flights.py
│   │   │   └── seats_aero.py
│   │   ├── analysis/
│   │   │   ├── features.py      # Z-scores, seasonality
│   │   │   └── alerts.py        # Threshold detection
│   │   ├── ai/
│   │   │   ├── prompts.py       # Claude prompt templates
│   │   │   └── enrichment.py    # Deal explanation generation
│   │   ├── notifications/
│   │   │   └── ntfy.py
│   │   └── api/
│   │       └── routes.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── hooks/
│   ├── Dockerfile
│   └── package.json
├── docs/
└── README.md
```
