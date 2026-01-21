# Walkabout Vision & Product Strategy

## Product Positioning

**For** high-intent travelers and points hobbyists who are tired of missing deals and overpaying for flights,

**Walkabout is** a self-hosted travel intelligence engine

**That** turns "price checking" into "automated deal hunting"

**Unlike** Google Flights alerts (single-source, no award tracking, no historical context),

**Walkabout** combines cash price tracking, award availability, and deal aggregation into a single dashboard where you own the data.

---

## The Problem

### Pain Points

1. **Fragmented Information**
   - Deals scattered across Secret Flying, OMAAT, TPG, airline emails
   - Award availability requires checking multiple airline sites
   - No single view of "what's good right now from my airport?"

2. **Lack of Context**
   - "Is $800 to LA good?" - depends on historical patterns you don't have
   - Google shows current prices but no "this is 20% below average"
   - No memory of what you've searched before

3. **Alert Fatigue**
   - Too many notifications = ignore everything
   - Generic alerts not filtered to YOUR routes
   - Miss the real deals in the noise

4. **Points Complexity**
   - Award availability changes constantly
   - Hard to know when to use points vs cash
   - Family travel (4+ seats) even harder to find

---

## The Solution: Personal Flight Deal Hub

### Three Pillars

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR FLIGHT DASHBOARD                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  A. DEAL FEEDS          B. AWARD MONITOR      C. PRICE TRACKER │
│  ───────────────        ────────────────      ──────────────── │
│  Aggregated deals       Points availability   Your routes with │
│  from multiple blogs    via Seats.aero        historical data  │
│  filtered to YOUR       for partner programs  "Is this good?"  │
│  home airport           Family-trip viable    context          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### A. Deal Feed Aggregator

**What it does:**
- Pulls RSS feeds from Secret Flying, OMAAT, The Points Guy, etc.
- Filters for deals from your home airport (AKL, etc.)
- Deduplicates across sources (same deal on 3 blogs = 1 card)
- Extracts price/route/dates from unstructured text (best-effort)

**Value:** "Someone else finds the deals, we filter for you"

### B. Award Flight Monitor

**What it does:**
- Polls Seats.aero API for award availability
- Tracks programs that can book Air NZ metal (United, Aeroplan, etc.)
- Filters for family-viable (4+ seats in same cabin)
- Alerts when availability appears

**Caveat:** Seats.aero does NOT track Airpoints directly. But Star Alliance partners can often book Air NZ flights with their miles.

**Value:** "Catch award seats before they disappear"

### C. Personal Price Tracker

**What it does:**
- Monitors YOUR specific routes (AKL→NAN, AKL→HNL, etc.)
- Stores price history over time
- Computes "is this good?" based on YOUR data
- Alerts on meaningful drops (not noise)

**Value:** "Know when it's actually a good time to book"

---

## Target Users

### Primary: The NZ Trip Planner

- Based in NZ (AKL/CHC/WLG)
- Planning 1-2 international trips per year
- Family of 4 (school holiday constraints)
- Cares about value, not necessarily cheapest
- Comfortable self-hosting on Unraid/Docker

### Secondary: The Points Hobbyist

- Actively manages multiple loyalty programs
- Wants to maximize redemption value
- Tracks award availability strategically
- Already uses Seats.aero or similar

### Tertiary: The Opportunistic Traveler

- Flexible on destination
- "I'll go wherever is cheap"
- Wants to see the best deals from their airport
- Less about specific routes, more about discovery

---

## Feature Hierarchy

### Must Have (MVP)
1. Deal feed ingestion + deduplication
2. User profile (home airport, watched destinations)
3. Deal cards filtered to user preferences
4. Push notifications for high-value matches
5. Basic dashboard UI

### Should Have (Phase 2)
1. Seats.aero integration for award tracking
2. Tracked route price history
3. "Good price" indicator based on history
4. Similar destination suggestions

### Nice to Have (Phase 3)
1. Advanced deal scoring/ranking
2. AI-powered deal explanations
3. Calendar heatmaps for pricing
4. Multi-user support

---

## What Walkabout Is NOT

- **Not a booking engine** - We surface deals, you book elsewhere
- **Not a scraping operation** - Prefers APIs and RSS where possible
- **Not multi-tenant SaaS** - Single-user, self-hosted focus
- **Not Google Flights replacement** - Complementary intelligence layer

---

## Success Metrics

After 30 days of use:

| Metric | Target |
|--------|--------|
| Deals surfaced per week | 10-20 relevant |
| False positive rate (irrelevant alerts) | <20% |
| Time to value (first useful alert) | <24 hours |
| User engagement (dashboard visits) | 3-5x/week |
| Deals acted on (clicked through) | 1-2/month |

---

## Competitive Landscape

| Solution | Pros | Cons | Walkabout Advantage |
|----------|------|------|---------------------|
| Google Flights Alerts | Free, reliable | Single source, no history, no awards | Aggregation + context |
| Secret Flying | Great deals | Manual checking, no filtering | Automated + filtered |
| Seats.aero | Best award data | Separate tool, no cash prices | Integrated dashboard |
| AwardHacker | Award routing | No availability, no cash | Live availability |
| Manual spreadsheet | Full control | Time-consuming | Automated |

---

## Technical Philosophy

1. **Single container** - Easy to deploy, backup, move
2. **SQLite by default** - No external database to manage
3. **APIs over scraping** - More reliable, less maintenance
4. **Raw-first data model** - Store everything, derive views
5. **Unraid-native** - First-class Unraid template support
