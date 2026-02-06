# Feature I: Skyscanner API Evaluation

**Beads ID**: walkabout-mvg.9
**Date**: 2026-02-06
**Status**: Complete — Recommendation: Deprecate

## Executive Summary

The current `SkyscannerSource` uses `skyscanner44.p.rapidapi.com`, an unofficial third-party RapidAPI wrapper. After evaluating the official Skyscanner Travel API and comparing data sources, the recommendation is to **deprecate Skyscanner as a source** and rely on SerpAPI (Google Flights) + Amadeus as the primary price data pipeline.

## Current Implementation

**File**: `backend/app/services/flight_price_fetcher.py`, lines 271-353

| Aspect | Current State |
|--------|--------------|
| API | `skyscanner44.p.rapidapi.com` (unofficial RapidAPI wrapper) |
| Auth | RapidAPI key (`X-RapidAPI-Key` header) |
| Endpoint | `GET /search` with IATA codes |
| Response | `itineraries.results[]` with `pricing_options` |
| Rate limit | Depends on RapidAPI plan (typically 500-1000/month on free/basic) |
| Cost | $0-$10/month depending on RapidAPI tier |
| Reliability | Moderate — third-party wrappers can break without notice |

## Official Skyscanner Travel API

Source: [Skyscanner Partners](https://www.partners.skyscanner.net/product/travel-api)

| Aspect | Official API |
|--------|-------------|
| Access | Partner application required, reviewed within 2 weeks |
| Requirement | "Established business with a large audience" |
| Cost | Free for approved partners (commission-based monetization) |
| Endpoints | Flights Live Prices, Flights Indicative Prices |
| Place codes | Sky entity codes (`-sky` suffix, e.g., `LOND-sky`) not IATA |
| Data | 1,200+ airline partners |
| Limitation | Must link users to Skyscanner for booking (affiliate model) |

### Barriers to Official API

1. **Partner approval**: Requires established business with large audience — Walkabout is a personal/small project
2. **Affiliate requirement**: Must route bookings through Skyscanner (Impact platform)
3. **Sky entity codes**: Not IATA codes — requires mapping layer (`AKL` → `AKLA-sky`)
4. **Indicative Prices API**: Cached/approximate, not live prices — useful for trends but not deal detection
5. **Live Prices API**: Creates sessions, requires polling — complex integration

## Comparison: Data Sources for Walkabout

| Factor | SerpAPI (Google Flights) | Amadeus | Skyscanner (RapidAPI) |
|--------|-------------------------|---------|----------------------|
| **Data quality** | Excellent — Google Flights data | Good — GDS data | Moderate — aggregated |
| **Price accuracy** | Browser-accurate (with deep_search) | Real-time GDS | Cached, may lag |
| **Price intelligence** | price_insights, price_level, history | Price Analysis quartiles | None |
| **Deal detection data** | Google's own low/typical/high | Historical quartiles | None |
| **NZ/AU coverage** | Excellent | Good | Good |
| **Authentication** | Simple API key | OAuth2 (client credentials) | RapidAPI key |
| **Reliability** | High (Google infrastructure) | High (airline GDS) | Low (third-party wrapper) |
| **Cost** | $50/month (5,000 searches) | Free (test: 10/sec, prod: 40/sec) | $0-10/month (limited) |
| **Unique value** | Price insights, deep search | Price Analysis, flight details | Booking URLs |
| **Breaking risk** | Low | Low | **High** — wrapper can disappear |

## Analysis

### Why Skyscanner Adds Little Value

1. **No unique data**: SerpAPI already provides Google Flights prices (superior accuracy) and Amadeus provides GDS prices. Skyscanner prices are aggregated from similar sources.

2. **No intelligence**: SerpAPI provides `price_insights` (Google's deal assessment) and Amadeus provides `itinerary-price-metrics` (historical quartiles). Skyscanner provides raw prices only.

3. **Reliability risk**: The `skyscanner44` wrapper is an unofficial third-party product on RapidAPI. It could break, change pricing, or disappear at any time. Both SerpAPI and Amadeus are first-party APIs with published SLAs.

4. **Maintenance burden**: Supporting 3 price sources means 3x the edge cases, error handling, and key configuration. The marginal value of a third source doesn't justify the maintenance cost.

5. **Booking URLs**: The one unique feature (deep links to booking) could be replicated by constructing Skyscanner/Google Flights URLs directly, without API access.

### Where Skyscanner Could Add Value (If Official API)

- **Indicative Prices**: Cheap cached prices useful for bulk route scanning (e.g., "which routes from AKL are cheapest this month")
- **Multi-city coverage**: Aggregates many OTAs for comparison
- **Historical trends**: Some trend data available to partners

But these are only available through the official partner API, which requires business-scale audience.

## Recommendation

### Deprecate Skyscanner Source

1. **Keep the code** but mark `SkyscannerSource` as deprecated with a code comment
2. **Move to last position** in the fallback chain (SerpAPI → Amadeus → Playwright → Skyscanner)
3. **Remove from Settings UI priority** — don't encourage new users to configure it
4. **Don't invest in improvements** — no new features for this source
5. **Document in Settings**: "Skyscanner integration uses an unofficial API wrapper. For best results, configure SerpAPI or Amadeus."

### If Skyscanner Official API Becomes Accessible

If Walkabout grows to qualify for official partner status:
1. Replace `skyscanner44` wrapper with official Indicative Prices API
2. Add Sky entity code mapping (IATA → `-sky` suffix)
3. Use for bulk route scanning (complement to targeted SerpAPI/Amadeus queries)
4. Integrate affiliate links for monetization

### Migration Plan (Not Needed Now)

No breaking changes — Skyscanner remains functional for existing users who have a RapidAPI key configured. It simply stops being the recommended source.

## Conclusion

The two-source strategy (SerpAPI for Google Flights accuracy + Amadeus for GDS depth) provides superior data quality, deal intelligence, and reliability compared to adding Skyscanner as a third source. The unofficial RapidAPI wrapper carries unnecessary breaking risk with minimal unique value.
