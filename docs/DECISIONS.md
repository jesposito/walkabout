# Project Decisions

## Answered Questions

### 1. API vs Self-Scraping

**Decision: Hybrid Approach**

| Data Source | Method | Cost | Rationale |
|-------------|--------|------|-----------|
| Cash fares (Google Flights) | Self-scrape with Playwright | Free | Working scrapers exist, 1-2 searches/day is fine |
| Award availability | Seats.aero API | ~$10/mo | No viable scraping option for airline award systems |
| Fallback | SerpAPI (if scraping breaks) | ~$50/mo | Insurance policy, can skip initially |

**Research finding**: Self-scraping Google Flights is viable for personal use. Multiple working Playwright-based scrapers on GitHub.

---

### 2. Miles Programs

**User has:**
- [x] Hawaiian/Alaska Atmos Rewards (primary)
- [x] Air NZ Airpoints (secondary)

**Decision**: Support these two initially, architecture allows adding more later.

**Miles value comparison will use:**
- Atmos: ~1.2 cpp (cents per point) typical value
- Airpoints: ~1.0 NZD per point typical value

---

### 3. Notifications

**Decision: ntfy (self-hosted)**

User mentioned Pushover/ntfy. Research shows ntfy is the better choice:
- Fully self-hostable on Unraid
- Simpler API than Pushover
- Both iOS and Android apps
- Supports action buttons ("View Deal", "Dismiss")
- Free (vs Pushover's one-time purchase)

---

### 4. Historical Analysis

**Decision: Meaningful analysis only**

User said: "would be excellent if it could be actually useful... If it doesn't actively help its not necessary"

**Implementation:**
- Z-score based anomaly detection (statistically meaningful)
- Seasonality tracking (builds over 12 months)
- Rolling percentiles (P10, P50, P90)
- AI explains patterns in natural language when relevant

**NOT implementing:**
- Generic "best day to book" advice (varies too much by route)
- Complex ML predictions (need 2+ years data, diminishing returns)

---

### 5. Resort Monitoring

**Decision: Phase 2**

User said: "Somewhere in the middle. Serve the goal..."

Flights are the bigger variable and cost driver. Resort monitoring comes after flight tracking is solid.

---

### 6. UI Complexity

**Decision: Goal-focused dashboard**

User said: "Serve the goal... save us money and enable us to get away once a year at least."

**MVP UI:**
- Current best deal (prominently displayed)
- "Should we book?" AI recommendation
- Price trend chart
- Next best alternatives
- Miles balance & comparison

**NOT MVP:**
- Complex analytics dashboards
- Data export features
- Multi-user support

---

### 7. AI Integration

**Decision: Claude API, strategically gated**

User specifically asked about AI/Claude making it better.

**Oracle consultation findings:**
> "Rules detect, AI explains and advises"

**Implementation:**
1. Rules/stats compute whether a deal is interesting (free)
2. AI only called when threshold crossed (cost-controlled)
3. AI generates natural language explanation + recommendation
4. Estimated cost: ~$2-5/month

**High-value AI use cases:**
1. Deal explanations ("This is 18% below average, during shoulder season")
2. "Should we book?" reasoning
3. Miles vs cash comparison advice
4. Weekly digest summaries

---

### 8. Geo-Arbitrage / Multi-Country Checking

**Decision: Not MVP, optional later**

**Research finding**: The hype is overblown.
- Real-world testing shows 5-15% variation, not 50%+
- USA Today (Jan 2026): "minimal savings" on flights
- Most of the "savings" come from currency arbitrage, not price differences

**If added later:**
- Single gluetun container with country rotation (not 8 containers)
- Use `ingestbot/randomizer` for scheduled rotation
- Only worth it if baseline data shows meaningful differences for NZ routes

---

## Technical Decisions

### Stack
| Component | Choice |
|-----------|--------|
| Backend | Python + FastAPI |
| Frontend | React + Tailwind |
| Database | PostgreSQL + TimescaleDB |
| Scraping | Playwright |
| Jobs | Celery + Redis |
| AI | Claude API (Anthropic) |
| Notifications | ntfy (self-hosted) |
| Container | Docker Compose |

### Data Refresh Schedule
| Data Type | Frequency |
|-----------|-----------|
| Google Flights prices | 2x daily (6am, 6pm) |
| Award availability (Seats.aero) | 1x daily |
| AI digest | Weekly (Sundays) |
| On-demand AI | When user asks |

---

## Open Items (Future Decisions)

- [ ] Specific Hawaii resorts to monitor (Phase 2)
- [ ] Additional destinations beyond Hawaii
- [ ] Whether to add geo-arbitrage based on actual data
- [ ] Multi-user support (if others want to use it)
