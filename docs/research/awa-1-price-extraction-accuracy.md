# Research: Price Extraction Accuracy

**Beads ID**: walkabout-awa.1.1 (research task for walkabout-awa.1)
**Date**: 2026-02-06
**Status**: Complete

---

## Table of Contents

1. [Current Architecture Analysis](#1-current-architecture-analysis)
2. [Bug Analysis: Three Critical Defects](#2-bug-analysis-three-critical-defects)
3. [Google Flights DOM Structure](#3-google-flights-dom-structure)
4. [Proposed Per-Row Extraction Design](#4-proposed-per-row-extraction-design)
5. [Bare Number Regex Recommendation](#5-bare-number-regex-recommendation)
6. [Confidence Scoring Changes](#6-confidence-scoring-changes)
7. [Risk Assessment and Migration Strategy](#7-risk-assessment-and-migration-strategy)
8. [Files That Will Need Changes](#8-files-that-will-need-changes)

---

## 1. Current Architecture Analysis

### File: `/home/jed/dev/walkabout/backend/app/scrapers/extractors.py`

The extraction system is built around four independent extractors and a unifier:

| Component | Lines | Purpose |
|-----------|-------|---------|
| `PriceValidator` | 39-98 | Validates extracted prices (range: $50-$50,000) |
| `AirlineValidator` | 101-181 | Validates airline names against known list + patterns |
| `StopsValidator` | 184-231 | Validates stop count (0-4, cross-validated with duration) |
| `DurationValidator` | 234-270 | Validates duration (30min to 48hr) |
| `PriceExtractor` | 289-452 | 21 strategies across 6 fallback levels for price extraction |
| `FlightDetailsExtractor` | 455-703 | 10 strategies each for airline, stops, duration |
| `UnifiedExtractor` | 733-821 | Combines all extractors into `FlightData` objects |

### Extraction Strategy Hierarchy (PriceExtractor)

The `PriceExtractor.STRATEGIES` list (lines 303-336) defines 21 strategies across 6 levels:

- **Level 0** (3 strategies): Data attributes (`data-gs`, `data-price`, `data-value`)
- **Level 1** (5 strategies): ARIA labels (`aria-label*='dollars'`, `*='NZD'`, etc.)
- **Level 2** (4 strategies): CSS classes (`.YMlIz`, `*='price'`, `*='amount'`, `*='fare'`)
- **Level 3** (2 strategies): Jsname attributes (`jsname='IWWDBc'`, `jsname*='rice'`)
- **Level 4** (4 strategies): Structural patterns (`div[class*='price'] span`, etc.)
- **Level 5** (3 strategies): Text patterns and full span scan (last resort)

### Price Regex Patterns (lines 339-348)

```python
PRICE_PATTERNS = [
    (r'NZ\$\s*([\d,]+)', "NZD prefix"),       # Best: currency-specific
    (r'AU\$\s*([\d,]+)', "AUD prefix"),
    (r'\$\s*([\d,]+)', "Dollar prefix"),
    (r'([\d,]+)\s*NZD', "NZD suffix"),
    (r'([\d,]+)\s*AUD', "AUD suffix"),
    (r'€\s*([\d,]+)', "Euro"),
    (r'£\s*([\d,]+)', "Pound"),
    (r'\b(\d{3,5})\b', "Bare number"),         # PROBLEM: matches anything
]
```

### FlightData Model (lines 710-731)

```python
@dataclass
class FlightData:
    price: Optional[int] = None
    price_confidence: float = 0.0
    price_strategy: str = ""
    airline: Optional[str] = None
    airline_confidence: float = 0.0
    stops: Optional[int] = None
    stops_confidence: float = 0.0
    duration_minutes: Optional[int] = None
    duration_confidence: float = 0.0
    overall_confidence: float = 0.0
    extraction_summary: Dict[str, Any] = field(default_factory=dict)
```

### UnifiedExtractor.extract_all() (lines 742-821)

This is where the critical index-matching bug lives. The method:

1. Extracts all prices as a flat list (line 750)
2. Extracts all airlines as a flat list (line 757)
3. Extracts all stops as a flat list (line 758)
4. Extracts all durations as a flat list (line 759)
5. Iterates over prices and matches other data **by array index** (line 764)

```python
for i, price_result in enumerate(price_results):
    flight = FlightData(price=price_result.value, ...)

    if airline_results:
        airline = airline_results[min(i, len(airline_results) - 1)]
        # ^^^ BUG: index matching assumes alignment
```

### Data Flow Through the Pipeline

```
extractors.py                    google_flights.py              scraping_service.py
─────────────                    ─────────────────              ───────────────────
PriceExtractor.extract()    ──►  UnifiedExtractor.extract_all() ──► scrape_route()
FlightDetailsExtractor.*()  ──►  Returns List[FlightData]       ──► ScrapeResult
                                                                     │
                                                                     ▼
                                                               _process_prices()
                                                                     │
                                                                     ├── Store ALL prices in DB
                                                                     ├── min(prices) for deal analysis
                                                                     └── PriceAnalyzer.analyze_price()
```

---

## 2. Bug Analysis: Three Critical Defects

### Bug 1: Index-Based Matching (extractors.py, line 764)

**Severity**: Critical

The `UnifiedExtractor.extract_all()` method extracts prices, airlines, stops, and durations as four independent flat lists, then pairs them by array position. This is fundamentally broken because:

1. **Different extraction strategies find different element counts.** A price selector might match 8 elements while the airline selector matches 5. The lists are different lengths with no correspondence.

2. **Deduplication breaks ordering.** Each extractor uses `seen` sets to deduplicate values (e.g., `seen_prices` at line 358). Two elements from the same flight row might be found by different strategies at different positions. After dedup, the insertion order has no relationship to page order.

3. **Confidence-based sorting destroys positional information.** Results are sorted by confidence (line 390: `results.sort(key=lambda x: x.confidence, reverse=True)`). A price from row 3 could end up at index 0 because it was found by a higher-confidence strategy.

4. **Clamping hides mismatches.** When lists have different lengths, the code uses `min(i, len(results) - 1)` (lines 773, 780, 787), which reuses the last element. If there are 10 prices but only 3 airlines, prices 4-10 all get airline 3.

**Impact**: Every `FlightData` object returned potentially has a price from one flight paired with an airline, stops count, and duration from a completely different flight.

### Bug 2: Bare Number Regex (extractors.py, line 347)

**Severity**: High

The pattern `r'\b(\d{3,5})\b'` matches any 3-5 digit number as a price. In the context of a Google Flights page, this matches:

- **Flight numbers**: "NZ 123", "QF 450" -> extracts 123, 450
- **Seat counts**: "350 seats" -> extracts 350
- **Distance**: "12,500 km" -> could match 12500
- **Page element IDs/counts**: Various UI numbers
- **Duration components**: "1435" in some time formats
- **Emission data**: "285 kg CO2" -> extracts 285

Because this regex is the *last* pattern tried (line 347), it only fires when no currency-prefixed pattern matches. However, when it fires on the Level 5 "all-spans" strategy (line 335, which scans ALL `<span>` elements on the page), it can extract dozens of false positives.

The `PriceValidator` (lines 39-98) catches some of these (rejecting values below $50 or in the `SUSPICIOUS_PRICES` set), but any flight number or arbitrary number between 50 and 50,000 passes validation.

### Bug 3: min() on Potentially Corrupted Data (scraping_service.py, line 175)

**Severity**: High

```python
best_price = min(flight_results, key=lambda x: x.price_nzd)
```

The deal analysis pipeline takes the *minimum* price from all extracted results and uses it for z-score calculation, new-low detection, and notification triggering. If extraction includes even one false positive (e.g., a flight number "350" extracted as a $350 price), that becomes the "best price" and:

1. Gets stored in the database as a real price point
2. May trigger a false "new low" deal alert
3. Poisons the historical price distribution for future z-score calculations
4. Sends a misleading notification to the user

The contamination is permanent: once a false price enters the `flight_prices` table, it affects all future `PriceAnalyzer.get_price_history()` calls for the next 90 days (line 116-117).

---

## 3. Google Flights DOM Structure

### Source: Open-Source Scraper Analysis

Based on analysis of the EDGEofMRI/Google-Flights-Scraper (Python + selectolax) and harsh-vardhhan/google-flight-scraping-playwright (JavaScript + Playwright), the Google Flights results page has a well-defined hierarchical DOM structure.

### Page Layout Hierarchy

```
Google Flights Results Page
├── Categories container (e.g., "Best departing flights", "Other departing flights")
│   CSS: .zBTtmb (category labels)
│
├── Category result groups
│   CSS: .Rk10dc (container for all flights in a category)
│   │
│   └── Individual flight result rows (CRITICAL: this is the row container)
│       CSS: .yR1fYc (alternative: li elements within a list)
│       │
│       ├── Airline info
│       │   CSS: .Ir0Voe .sSHqwe (airline company name)
│       │   Also: img[alt] for airline logos
│       │
│       ├── Duration
│       │   CSS: .AdWm1c.gvkrdb (total travel time, e.g., "13 hr 45 min")
│       │
│       ├── Stops
│       │   CSS: .EfT7Ae .ogfYpf (e.g., "Nonstop", "1 stop")
│       │
│       ├── Emissions
│       │   CSS: .V1iAHe .AdWm1c (CO2 data)
│       │
│       ├── Price container
│       │   CSS: .U3gSDe .FpEdX span (price text, e.g., "$1,234")
│       │   Also: .YMlIz (observed in other scrapers)
│       │
│       └── Trip type
│           CSS: .U3gSDe .N872Rd (e.g., "round trip")
│
└── "More flights" button
    CSS: .zISZ5c button
```

### Key Selectors for Row-Based Extraction

| Element | Primary Selector | Fallback Selectors | Notes |
|---------|-----------------|-------------------|-------|
| **Flight row container** | `.yR1fYc` | `li[class*='pIav2d']`, `[jsname='IWWDBc']` parent traversal | Each row = one flight option |
| **Category container** | `.Rk10dc` | `[class*='result']` | Groups flights by "Best" vs "Other" |
| **Category label** | `.zBTtmb` | `h3`, `[role="heading"]` | "Best departing flights" etc. |
| **Airline name** | `.Ir0Voe .sSHqwe` | `[data-carrier]`, `img[alt*='airline']` | Text content is airline name |
| **Duration** | `.AdWm1c.gvkrdb` | `[aria-label*='duration']`, `[class*='duration']` | Format: "13 hr 45 min" |
| **Stops** | `.EfT7Ae .ogfYpf` | `[aria-label*='stop']`, `[class*='stop']` | "Nonstop" or "1 stop" etc. |
| **Price** | `.U3gSDe .FpEdX span` | `.YMlIz`, `[aria-label*='dollars']` | Currency symbol + number |
| **Trip type** | `.U3gSDe .N872Rd` | N/A | "round trip" etc. |

### Alternative DOM Access Pattern

The harsh-vardhhan scraper takes a different approach: instead of using CSS selectors for individual flight rows, it iterates all `<a>` (anchor/link) elements and checks if each contains airline name + price + duration text. This works because each flight result row is typically wrapped in or contains a clickable link. However, this is less reliable than structural CSS selectors.

### Important DOM Caveats

1. **Google obfuscates class names.** Classes like `.yR1fYc`, `.Ir0Voe`, `.sSHqwe` are generated names that change periodically with Google UI updates. They are NOT stable long-term.

2. **ARIA labels are more stable.** Accessibility attributes (`aria-label`, `role`) change less frequently because they serve accessibility compliance purposes.

3. **Data attributes are most reliable** when present. `data-gs`, `data-price`, `[jsname]` attributes are internal Google identifiers.

4. **The page uses dynamic rendering.** Content loads asynchronously; waiting for `networkidle` or specific selectors is essential.

5. **"More flights" button** (`.zISZ5c button`) must be clicked to reveal all results. Without clicking it, only the "Best" category is visible.

### No Saved HTML Snapshots

The project has directories configured for HTML snapshots (`/app/data/html_snapshots/`) but the local `data/` directory does not exist (it is a Docker-internal path). No snapshots are available for offline analysis. The `_save_failure_artifacts()` method (google_flights.py, lines 193-225) saves these only on failure, not on success.

**Recommendation**: Add a "save snapshot on success" option (debug mode) to capture real DOM for offline development and testing.

---

## 4. Proposed Per-Row Extraction Design

### Core Principle

Instead of extracting prices, airlines, stops, and durations as four independent flat lists, extract them as correlated tuples within each flight row container.

### Architecture Overview

```
CURRENT (broken):
  Page → PriceExtractor.extract(page) → [price1, price2, ...]
  Page → FlightDetailsExtractor.extract_airline(page) → [airline1, airline2, ...]
  Page → FlightDetailsExtractor.extract_stops(page) → [stops1, stops2, ...]
  Page → FlightDetailsExtractor.extract_duration(page) → [dur1, dur2, ...]
  Merge by index → FlightData(price1, airline1, stops1, dur1) ← WRONG

PROPOSED (correct):
  Page → find_flight_rows(page) → [row1, row2, ...]
  For each row:
    row → extract_price(row) → price
    row → extract_airline(row) → airline
    row → extract_stops(row) → stops
    row → extract_duration(row) → duration
    → FlightData(price, airline, stops, duration) ← CORRECT
```

### Implementation Design

#### Phase 1: Row Discovery

Create a new `FlightRowLocator` class that finds individual flight row containers:

```python
class FlightRowLocator:
    """Locate individual flight result rows on the page."""

    # Row container strategies in priority order
    ROW_STRATEGIES = [
        # Level 0: Most specific Google Flights selectors
        {"name": "yR1fYc", "selector": ".yR1fYc", "level": 0},
        {"name": "pIav2d", "selector": "li[class*='pIav2d']", "level": 0},

        # Level 1: Category-scoped row discovery
        {"name": "rk10dc-children", "selector": ".Rk10dc > div", "level": 1},
        {"name": "result-list-li", "selector": "[class*='result'] li", "level": 1},

        # Level 2: ARIA-based (more stable)
        {"name": "role-listitem", "selector": "[role='listitem']", "level": 2},
        {"name": "aria-flight-row", "selector": "[aria-label*='flight']", "level": 2},

        # Level 3: Structural (generic)
        {"name": "flight-card", "selector": "[class*='flight-card'], [class*='flightCard']", "level": 3},
        {"name": "price-parent", "selector": None, "level": 3},  # Dynamic: find price, traverse to row
    ]

    @classmethod
    async def find_rows(cls, page: Page) -> List[ElementHandle]:
        """Find all flight result row containers."""
        ...
```

The key insight: a valid flight row MUST contain both a price element AND an airline name. Rows that lack either are not flight results.

#### Phase 2: Per-Row Extraction

Modify the existing extractors to work on an `ElementHandle` (a row) instead of the full `Page`:

```python
class RowExtractor:
    """Extract flight data from a single row container."""

    @classmethod
    async def extract_from_row(cls, row: ElementHandle) -> Optional[FlightData]:
        """Extract all flight data fields from a single row element."""
        price = await cls._extract_price(row)
        if price is None:
            return None  # No price = not a valid flight row

        airline = await cls._extract_airline(row)
        stops = await cls._extract_stops(row)
        duration = await cls._extract_duration(row)

        return FlightData(
            price=price.value,
            price_confidence=price.confidence,
            airline=airline.value if airline else None,
            airline_confidence=airline.confidence if airline else 0.0,
            stops=stops.value if stops else None,
            stops_confidence=stops.confidence if stops else 0.0,
            duration_minutes=duration.value if duration else None,
            duration_confidence=duration.confidence if duration else 0.0,
        )
```

#### Phase 3: Fallback to Page-Level Extraction

The per-row approach should be the primary strategy, but the existing page-level extraction should remain as a degraded fallback for when Google changes their DOM structure enough that row containers cannot be found:

```python
class UnifiedExtractor:
    @classmethod
    async def extract_all(cls, page: Page) -> List[FlightData]:
        # Strategy 1: Per-row extraction (preferred)
        rows = await FlightRowLocator.find_rows(page)
        if rows:
            flights = []
            for row in rows:
                flight = await RowExtractor.extract_from_row(row)
                if flight:
                    flights.append(flight)
            if flights:
                return flights

        # Strategy 2: Page-level extraction (fallback, mark lower confidence)
        return await cls._extract_page_level(page)
```

#### Phase 4: Row Validation

A discovered row is valid only if it contains correlated data:

```python
class RowValidator:
    @classmethod
    def validate_row(cls, flight: FlightData) -> bool:
        """A valid flight row must have at minimum a price."""
        if flight.price is None:
            return False
        if flight.price < 50 or flight.price > 50000:
            return False
        return True

    @classmethod
    def cross_validate(cls, flight: FlightData) -> float:
        """Cross-validate fields for consistency. Returns confidence adjustment."""
        adjustments = 0.0

        # Duration vs stops cross-validation
        if flight.stops is not None and flight.duration_minutes is not None:
            if flight.stops == 0 and flight.duration_minutes > 24 * 60:
                adjustments -= 0.2  # Nonstop but > 24hr is suspicious
            if flight.stops >= 2 and flight.duration_minutes < 120:
                adjustments -= 0.2  # 2+ stops but < 2hr is suspicious

        return adjustments
```

### Selector Strategy for Row Containers

The recommended approach is a multi-level fallback:

1. **Primary**: `.Rk10dc .yR1fYc` -- flight rows within result categories
2. **Secondary**: `li` elements within the results area that contain both a price element and airline text
3. **Tertiary**: Dynamic discovery -- find all price elements, then traverse up the DOM tree to find the nearest common ancestor that also contains airline/duration text
4. **Quaternary**: Fall back to page-level extraction with lower confidence scores

The dynamic discovery (tertiary) approach is especially important because it is DOM-structure-agnostic:

```python
async def _discover_rows_from_prices(cls, page: Page) -> List[ElementHandle]:
    """Find rows by locating prices and traversing up to row containers."""
    price_elements = await page.query_selector_all("[aria-label*='dollars'], .YMlIz, .FpEdX")

    rows = []
    for price_el in price_elements:
        # Walk up the DOM to find the row-level container
        # A row container typically has airline + duration + stops as siblings/descendants
        row = await cls._find_row_ancestor(page, price_el)
        if row:
            rows.append(row)

    return rows
```

---

## 5. Bare Number Regex Recommendation

### Current Pattern

```python
(r'\b(\d{3,5})\b', "Bare number")  # Line 347
```

### Recommendation: Remove from Default Patterns, Add Restricted Version as Emergency Fallback

**Remove it from `PRICE_PATTERNS`.** The bare number regex is the primary source of false positive prices. It matches:

- Flight numbers (e.g., NZ123 -> "123")
- Seat counts, distances, emission numbers
- Duration components, page IDs, element counts

**Replace with a contextual pattern** that only matches bare numbers when they appear near currency context:

```python
PRICE_PATTERNS = [
    (r'NZ\$\s*([\d,]+)', "NZD prefix"),
    (r'AU\$\s*([\d,]+)', "AUD prefix"),
    (r'\$\s*([\d,]+)', "Dollar prefix"),
    (r'([\d,]+)\s*NZD', "NZD suffix"),
    (r'([\d,]+)\s*AUD', "AUD suffix"),
    (r'€\s*([\d,]+)', "Euro"),
    (r'£\s*([\d,]+)', "Pound"),
    # REMOVED: bare number regex
]
```

If absolutely needed as an emergency fallback, restrict it:

```python
# Only match bare numbers within elements that have price-related ARIA labels or class names
# AND only when currency-aware patterns have completely failed
EMERGENCY_PRICE_PATTERN = (r'\b(\d{3,5})\b', "Bare number (emergency)")
```

This emergency pattern should ONLY be applied within elements that have already been identified as likely price containers (via ARIA label, class name, or structural position), never on arbitrary `<span>` elements.

### Risk of Removal

- **Low risk**: If the page displays prices with currency symbols (Google Flights always does for NZD), the currency-aware patterns will match.
- **Edge case**: If Google switches to a locale where prices display without any currency indicator, the bare number pattern would be needed. However, since the scraper sets `curr=NZD&hl=en`, prices always show with `$` or `NZ$`.
- **Mitigation**: The emergency fallback pattern restricted to price-context elements covers this edge case without the false positive risk.

---

## 6. Confidence Scoring Changes

### Current Confidence Model

Currently, confidence is calculated per-field independently:

```python
# Price confidence (line 437-438)
level_penalty = level * 0.05
confidence = min(validation.confidence - level_penalty, 0.99)

# Overall confidence (lines 793-801)
flight.overall_confidence = sum(confidences) / len(confidences)
```

### Proposed Confidence Model

#### Per-Row Confidence

Add a new dimension to confidence: **correlation confidence**. This measures how certain we are that the extracted fields actually belong to the same flight.

```python
@dataclass
class FlightData:
    # Existing fields...
    price_confidence: float = 0.0
    airline_confidence: float = 0.0
    stops_confidence: float = 0.0
    duration_confidence: float = 0.0

    # NEW fields
    correlation_confidence: float = 0.0  # How sure are we these fields are from the same flight?
    extraction_method: str = ""          # "per_row" or "page_level"
    overall_confidence: float = 0.0
```

#### Confidence Calculation

```python
def calculate_overall_confidence(flight: FlightData) -> float:
    """Calculate overall confidence incorporating correlation."""
    field_confidences = [flight.price_confidence]
    if flight.airline_confidence > 0:
        field_confidences.append(flight.airline_confidence)
    if flight.stops_confidence > 0:
        field_confidences.append(flight.stops_confidence)
    if flight.duration_confidence > 0:
        field_confidences.append(flight.duration_confidence)

    field_avg = sum(field_confidences) / len(field_confidences)

    # Weight correlation heavily -- incorrect correlation is worse than
    # slightly inaccurate individual fields
    return field_avg * 0.4 + flight.correlation_confidence * 0.6
```

#### Correlation Confidence Values

| Extraction Method | Correlation Confidence | Rationale |
|------------------|----------------------|-----------|
| Per-row: specific selector (`.yR1fYc`) | 0.95 | High confidence data is from same row |
| Per-row: ARIA-based row | 0.90 | Good confidence, ARIA structure is reliable |
| Per-row: DOM traversal from price | 0.80 | Moderate -- ancestor traversal may be wrong |
| Page-level: index matching | 0.30 | Low -- index matching is unreliable |
| Page-level: single result only | 0.70 | OK -- if only 1 result, no pairing issue |

#### Cross-Validation Adjustments

After initial confidence calculation, apply cross-validation bonuses/penalties:

| Cross-Validation Check | Adjustment | Condition |
|----------------------|------------|-----------|
| Duration consistent with stops | +0.05 | Nonstop < 20hr, 1-stop has reasonable layover |
| Duration inconsistent with stops | -0.15 | Nonstop > 24hr, or 2+ stops < 3hr |
| Price in typical range for route | +0.05 | Within 1 stddev of historical mean |
| Price extreme outlier | -0.20 | More than 3 stddev from historical mean |
| All 4 fields extracted | +0.05 | Complete data suggests valid row |
| Only price extracted | -0.10 | May be a non-flight price element |

#### Minimum Confidence Threshold for Deal Analysis

Add a confidence gate before deal analysis in `scraping_service.py`:

```python
# Only consider flights with sufficient confidence for deal analysis
MIN_CONFIDENCE_FOR_DEALS = 0.60

confident_results = [f for f in flight_results if f.raw_data.get('overall_confidence', 0) >= MIN_CONFIDENCE_FOR_DEALS]

if confident_results:
    best_price = min(confident_results, key=lambda x: x.price_nzd)
    # ... analyze for deals
else:
    logger.warning("No flight results met confidence threshold for deal analysis")
```

---

## 7. Risk Assessment and Migration Strategy

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Google changes DOM, breaking row selectors | High (happens periodically) | Medium | Multi-level fallback chain + page-level fallback |
| Per-row extraction finds fewer results than page-level | Medium | Low | Fall back to page-level; log for monitoring |
| Removing bare number regex causes missed prices | Low | Low | Emergency fallback with context restriction |
| Historical data contaminated with false prices | Already happened | High | Consider data cleanup script for outliers |
| "More flights" button not clicked, fewer results | Medium | Medium | Ensure click-to-expand is attempted before extraction |

### Migration Strategy

#### Phase 1: Non-Breaking Additions (Low Risk)

1. Add `FlightRowLocator` class alongside existing extractors
2. Add `RowExtractor` class that works within a row element
3. Add success-mode HTML snapshot capture for development
4. Add integration tests with saved HTML snapshots
5. **No changes to `UnifiedExtractor.extract_all()` yet**

#### Phase 2: Parallel Execution (Medium Risk)

1. Modify `UnifiedExtractor.extract_all()` to run BOTH strategies
2. Log both results for comparison (per-row vs page-level)
3. Return per-row results if available, page-level otherwise
4. Monitor logs for divergence between strategies
5. Remove bare number regex from default patterns

#### Phase 3: Confidence Gate (Medium Risk)

1. Add `correlation_confidence` and `extraction_method` to `FlightData`
2. Add confidence threshold gate in `scraping_service.py` before deal analysis
3. Ensure notifications only fire for high-confidence prices
4. Add data quality monitoring

#### Phase 4: Cleanup (Low Risk)

1. Remove page-level extraction as primary path (keep as fallback)
2. Consider historical data cleanup for obvious false positives
3. Add dashboard metrics for extraction method distribution

### Testing Strategy

1. **Capture real HTML snapshots**: Add a debug mode that saves page HTML on successful scrapes
2. **Unit tests with snapshots**: Test `FlightRowLocator` and `RowExtractor` against saved snapshots
3. **Comparison tests**: Run both old and new extraction on same snapshot, compare results
4. **Regression monitoring**: Log extraction method and confidence in `raw_data` for every stored price

### Backward Compatibility

- The `FlightData` dataclass gains new optional fields -- backward compatible
- The `FlightResult` and `ScrapeResult` dataclasses in `google_flights.py` are unchanged
- The `FlightPrice` model in the database is unchanged (confidence is stored in `raw_data` JSON)
- The `PriceAnalyzer` is unchanged but receives cleaner data

---

## 8. Files That Will Need Changes

### Must Change

| File | Changes |
|------|---------|
| `backend/app/scrapers/extractors.py` | Add `FlightRowLocator`, `RowExtractor`, `RowValidator`; modify `UnifiedExtractor.extract_all()`; remove bare number regex from `PRICE_PATTERNS`; modify per-element extractors to accept `ElementHandle` scope |
| `backend/app/services/scraping_service.py` | Add confidence threshold gate before `min()` deal analysis (line 175); log extraction method |

### Should Change

| File | Changes |
|------|---------|
| `backend/app/scrapers/google_flights.py` | Add success-mode HTML snapshot capture; ensure "More flights" button click; pass page structure hints to extractor |
| `backend/app/models/flight_price.py` | No schema changes needed (confidence in `raw_data` JSON) |

### New Files

| File | Purpose |
|------|---------|
| `backend/tests/test_extractors.py` | Unit tests for `FlightRowLocator`, `RowExtractor`, per-row extraction |
| `backend/tests/fixtures/` | Saved HTML snapshot fixtures for testing |

### May Change (Phase 4)

| File | Changes |
|------|---------|
| `backend/app/services/price_analyzer.py` | Add confidence-weighted analysis; historical data cleanup utility |
| `backend/app/services/notification.py` | Include confidence score in deal notifications |

---

## Summary of Recommendations

1. **Implement per-row extraction** as the primary strategy, keeping page-level as a fallback
2. **Remove the bare number regex** (`\b(\d{3,5})\b`) from default price patterns
3. **Add correlation confidence** to track how certain we are that extracted fields belong to the same flight
4. **Gate deal analysis** behind a minimum confidence threshold to prevent false positives
5. **Capture HTML snapshots on success** (debug mode) for offline development and test fixtures
6. **Click "More flights" button** before extraction to get the full result set
7. **Monitor extraction quality** by logging method and confidence with every stored price
8. **Consider historical data cleanup** for obvious false positive prices already in the database
