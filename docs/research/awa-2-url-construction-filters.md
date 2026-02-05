# Research: Google Flights URL Construction and Filter Passthrough

**Beads ID**: walkabout-awa.2.1
**Feature**: walkabout-awa.2 (URL Construction and Filter Passthrough)
**Date**: 2026-02-06

---

## 1. Current URL Construction Analysis

### 1.1 Three Separate URL Builders

There are **three independent implementations** that build Google Flights URLs, all with the same deficiencies:

#### A. `GoogleFlightsScraper._build_url()` (Scraper)

**File**: `/home/jed/dev/walkabout/backend/app/scrapers/google_flights.py` (lines 142-168)

```python
def _build_url(
    self,
    origin: str,
    destination: str,
    departure_date: date,
    return_date: Optional[date],
    adults: int = 2,
    children: int = 2
) -> str:
    dep_str = departure_date.strftime("%Y-%m-%d")
    url = (
        f"{self.BASE_URL}?q=flights%20from%20{origin}%20to%20{destination}"
        f"%20on%20{dep_str}"
    )
    if return_date:
        ret_str = return_date.strftime("%Y-%m-%d")
        url += f"%20return%20{ret_str}"
    url += f"&curr=NZD&hl=en"
    return url
```

**Parameters accepted but NOT used in URL**: `adults`, `children` (accepted as args but never appended)
**Parameters NOT accepted at all**: `cabin_class`, `stops_filter`, `infants_in_seat`, `infants_on_lap`, `carry_on_bags`, `checked_bags`, `include_airlines`, `exclude_airlines`, `currency` (hardcoded to NZD)

#### B. `build_google_flights_url()` (Template Helper for Booking Links)

**File**: `/home/jed/dev/walkabout/backend/app/utils/template_helpers.py` (lines 10-33)

```python
def build_google_flights_url(
    origin: str, destination: str, departure_date: date,
    return_date: Optional[date] = None, adults: int = 1,
    children: int = 0, cabin_class: str = "economy",
    currency: str = "NZD"
) -> str:
    cabin_map = {"economy": "1", "premium_economy": "2", "business": "3", "first": "4"}
    cabin_code = cabin_map.get(cabin_class.lower(), "1")  # Computed but never used!
    # ...builds URL without cabin_code, adults, children...
    return f"{base}?{'&'.join(query_parts)}"
```

**Key issue**: `cabin_code` is computed from the `cabin_map` but **never appended** to the URL. `adults` and `children` are accepted but ignored.

#### C. `TripPlanSearch._build_booking_url()` (Trip Plan Booking Links)

**File**: `/home/jed/dev/walkabout/backend/app/services/trip_plan_search.py` (lines 345-361)

```python
def _build_booking_url(self, origin, destination, departure_date, return_date) -> str:
    dep_str = departure_date.strftime("%Y-%m-%d")
    url = f"https://www.google.com/travel/flights?q=flights%20from%20{origin}%20to%20{destination}%20on%20{dep_str}"
    if return_date:
        ret_str = return_date.strftime("%Y-%m-%d")
        url += f"%20return%20{ret_str}"
    url += "&curr=NZD&hl=en"
    return url
```

**Parameters NOT accepted at all**: Everything except origin, destination, dates. Currency is hardcoded.

### 1.2 Caller Analysis - What Parameters Are Available but Dropped

#### ScrapingService (lines 77-85)

Passes `adults` and `children` from `SearchDefinition` but does NOT pass `cabin_class`, `stops_filter`, `infants_in_seat`, `infants_on_lap`, `carry_on_bags`, `checked_bags`, `currency`:

```python
result = await self.scraper.scrape_route(
    search_definition_id=search_def.id,
    origin=search_def.origin,
    destination=search_def.destination,
    departure_date=departure_date,
    return_date=return_date,
    adults=search_def.adults,
    children=search_def.children
    # Missing: cabin_class, stops_filter, infants_*, bags, currency
)
```

#### API booking URL builder (lines 286-295)

Passes `cabin_class` and `currency` but they are not used in the URL:

```python
booking_url = build_google_flights_url(
    origin=definition.origin,
    destination=definition.destination,
    departure_date=price.departure_date,
    return_date=price.return_date,
    adults=definition.adults,
    children=definition.children,
    cabin_class=definition.cabin_class.value,
    currency=definition.currency,
    # Missing: stops_filter, infants_*, bags
)
```

#### PlaywrightSource (flight_price_fetcher.py, lines 390-398)

Does NOT pass `cabin_class` at all despite having it available:

```python
result = await scraper.scrape_route(
    search_definition_id=0,
    origin=origin,
    destination=destination,
    departure_date=departure_date,
    return_date=return_date,
    adults=adults,
    children=children,
    # Missing: cabin_class, stops_filter, etc.
)
```

---

## 2. SearchDefinition Model - All Available Filter Fields

**File**: `/home/jed/dev/walkabout/backend/app/models/search_definition.py`

| Field | Type | Default | Currently Used in URL? |
|-------|------|---------|----------------------|
| `origin` | String(3) | required | Yes |
| `destination` | String(3) | required | Yes |
| `trip_type` | TripType enum | ROUND_TRIP | Partially (return_date presence) |
| `departure_date_start` | Date | nullable | Yes (via date generation) |
| `departure_date_end` | Date | nullable | Yes (via date generation) |
| `adults` | Integer | 2 | Accepted but NOT appended to URL |
| `children` | Integer | 2 | Accepted but NOT appended to URL |
| `infants_in_seat` | Integer | 0 | **No** - not passed to scraper |
| `infants_on_lap` | Integer | 0 | **No** - not passed to scraper |
| `cabin_class` | CabinClass enum | ECONOMY | **No** - not passed to scraper |
| `stops_filter` | StopsFilter enum | ANY | **No** - not passed to scraper |
| `include_airlines` | String(100) | nullable | **No** - not passed to scraper |
| `exclude_airlines` | String(100) | nullable | **No** - not passed to scraper |
| `currency` | String(3) | "NZD" | **Hardcoded** - not from model |
| `locale` | String(10) | "en-NZ" | **Hardcoded** `hl=en` |
| `carry_on_bags` | Integer | 0 | **No** - not passed to scraper |
| `checked_bags` | Integer | 0 | **No** - not passed to scraper |

### Enum Definitions

```python
class CabinClass(str, enum.Enum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"

class StopsFilter(str, enum.Enum):
    ANY = "any"
    NONSTOP = "nonstop"
    ONE_STOP = "one_stop"
    TWO_PLUS = "two_plus"
```

---

## 3. Google Flights URL Parameter Reference

### 3.1 URL Formats

Google Flights supports two URL formats:

#### Format A: Natural Language Query (Current - Used by Walkabout)

```
https://www.google.com/travel/flights?q=flights%20from%20AKL%20to%20LAX%20on%202026-04-01%20return%202026-04-15&curr=NZD&hl=en
```

This format uses a natural language `q=` parameter. Google parses it server-side and redirects/renders the search results. This format is simple but **does not support** most filter parameters like stops, cabin class, passengers, or bags. It only supports:

- Origin and destination (in the `q=` text)
- Departure date (in the `q=` text)
- Return date (in the `q=` text)
- `curr=` (currency)
- `hl=` (language)

**Limitation**: This is the format Walkabout currently uses, and it inherently cannot express stops, cabin, passengers, or bags.

#### Format B: Structured `tfs=` Parameter (Protobuf-encoded)

```
https://www.google.com/travel/flights/search?tfs=CBwQAho...&hl=en&gl=us&curr=USD
```

This format uses a protobuf-encoded `tfs=` (Travel Flight Search) parameter that encodes the entire search specification including:
- Origin/destination airports
- Dates
- Cabin class
- Number of stops
- Passenger counts
- Airline filters
- Bag counts

**Complexity**: The `tfs=` parameter is a base64-encoded protocol buffer. Constructing it requires understanding Google's internal protobuf schema, which is undocumented and reverse-engineered. This is fragile and likely to break when Google updates their format.

### 3.2 SerpAPI Parameters (Authoritative Reference)

The SerpAPI Google Flights engine provides a well-documented parameter set that maps to Google's internal parameters. Source: `serpapi/serpapi-mcp` repo (`engines/google_flights.json`).

#### Stops Filter

| SerpAPI `stops` Value | Meaning |
|----------------------|---------|
| `0` | Any number of stops (default) |
| `1` | Nonstop only |
| `2` | 1 stop or fewer |
| `3` | 2 stops or fewer |

**Mapping from SearchDefinition.StopsFilter**:

| StopsFilter Enum | SerpAPI `stops` Value |
|-----------------|----------------------|
| `ANY` | `0` |
| `NONSTOP` | `1` |
| `ONE_STOP` | `2` |
| `TWO_PLUS` | `3` |

#### Cabin Class (Travel Class)

| SerpAPI `travel_class` Value | Meaning |
|------------------------------|---------|
| `1` | Economy (default) |
| `2` | Premium Economy |
| `3` | Business |
| `4` | First |

**Mapping from SearchDefinition.CabinClass**:

| CabinClass Enum | SerpAPI `travel_class` Value |
|----------------|----------------------------|
| `ECONOMY` | `1` |
| `PREMIUM_ECONOMY` | `2` |
| `BUSINESS` | `3` |
| `FIRST` | `4` |

#### Passenger Counts

| SerpAPI Parameter | Default | Description |
|-------------------|---------|-------------|
| `adults` | `1` | Number of adult passengers |
| `children` | `0` | Number of children (ages 2-11) |
| `infants_in_seat` | `0` | Number of infants with own seat |
| `infants_on_lap` | `0` | Number of lap infants |

#### Bags

| SerpAPI Parameter | Default | Description |
|-------------------|---------|-------------|
| `bags` | `0` | Number of carry-on bags. Should not exceed total passengers with carry-on allowance (adults + children + infants_in_seat). |

**Note**: SerpAPI's `bags` parameter maps to carry-on bags. Checked bags are NOT directly supported as a URL parameter by Google Flights -- they are typically a post-search filter applied in the UI.

#### Airline Filters

| SerpAPI Parameter | Description |
|-------------------|-------------|
| `include_airlines` | Comma-separated IATA codes (e.g., `NZ,QF,HA`). Cannot be used with `exclude_airlines`. Also supports alliance values: `STAR_ALLIANCE`, `SKYTEAM`, `ONEWORLD`. |
| `exclude_airlines` | Comma-separated IATA codes to exclude. Cannot be used with `include_airlines`. |

#### Other Useful Parameters

| SerpAPI Parameter | Description |
|-------------------|-------------|
| `sort_by` | `1`=Top flights, `2`=Price, `3`=Departure time, `4`=Arrival time, `5`=Duration, `6`=Emissions |
| `max_price` | Maximum ticket price |
| `max_duration` | Maximum flight duration in minutes |
| `outbound_times` | Time range filter (e.g., `4,18` for 4AM-7PM departure) |
| `return_times` | Return time range filter |
| `layover_duration` | Layover duration range in minutes (e.g., `90,330`) |
| `exclude_conns` | Connecting airports to exclude |

### 3.3 Direct Google Flights URL Parameters (Non-SerpAPI)

When constructing URLs that open directly in a user's browser (booking links), the natural language `q=` format is the most reliable approach. However, several query string parameters ARE supported alongside it:

| Parameter | Description | Confirmed Working |
|-----------|-------------|-------------------|
| `curr` | Currency code (e.g., `NZD`, `USD`) | Yes |
| `hl` | Language (e.g., `en`) | Yes |
| `gl` | Country/region (e.g., `nz`, `us`) | Yes |
| `tfs` | Protobuf-encoded search (includes all filters) | Yes, but fragile |

**Key insight**: For **booking links** (user-facing URLs), the `q=` format is acceptable because it opens the correct search and the user can refine filters. For **scraping**, we need the filters to be applied before page load -- and the `q=` format does not support this.

### 3.4 Recommended Approach: Dual Strategy

1. **For scraping (Playwright)**: Use `tfs=` protobuf encoding OR apply filters via Playwright UI interaction after page load
2. **For booking links (user-facing)**: Use the `q=` format but add `tfs=` for filter pre-selection where possible
3. **For SerpAPI**: Already has a well-defined parameter interface -- just pass all the parameters through

---

## 4. Currency Verification

### 4.1 Current State

The currency is hardcoded to `NZD` in all three URL builders. The `SearchDefinition` model has a `currency` field (default `"NZD"`) that is never actually used in URL construction.

### 4.2 How `&curr=NZD` Works

The `curr` parameter tells Google Flights which currency to display prices in. Google will convert prices from the airline's base currency. This works regardless of the user's IP geolocation.

### 4.3 IP Geolocation Conflict

If the user's IP geolocates to a different country (e.g., the scraper runs from a US-based VPS), Google may:

1. Initially display in the geolocated currency (USD)
2. Override with `curr=NZD` if the parameter is present
3. Show a currency mismatch warning in some edge cases

The browser context in `google_flights.py` already sets `locale="en-NZ"` and `timezone_id="Pacific/Auckland"` (lines 266-268), which helps signal the NZ context, but the `curr=NZD` parameter is the primary mechanism.

### 4.4 DOM Currency Detection

To verify the actual displayed currency after page load, check:

1. **Price aria-labels**: `span[aria-label*='NZD']` or `span[aria-label*='New Zealand']`
2. **Currency symbol in price text**: Look for `NZ$` or `$` with NZD context
3. **Page metadata**: Google Flights may include a `data-currency` attribute on result containers
4. **URL after redirect**: After the page loads, the URL may contain currency info in the `tfs=` parameter

**Proposed verification approach**:
```python
# After page load, verify currency:
currency_indicators = [
    "span[aria-label*='NZ']",
    "span[aria-label*='New Zealand dollar']",
]
# Also check the displayed price text for currency symbol
page_text = await page.inner_text("body")
if "NZ$" in page_text or "NZD" in page_text:
    currency_confirmed = True
```

### 4.5 Recommendation

- Use the `currency` field from `SearchDefinition` instead of hardcoding `NZD`
- Add optional currency verification after page load (warning-level, not blocking)
- Consider adding `gl=nz` parameter to reinforce the New Zealand context

---

## 5. Existing SerpAPI/Skyscanner Parameter Handling

### 5.1 SerpAPISource (flight_price_fetcher.py, lines 104-181)

The SerpAPI source **already handles** cabin class correctly:

```python
params = {
    "engine": "google_flights",
    "departure_id": origin,
    "arrival_id": destination,
    "outbound_date": departure_date.isoformat(),
    "currency": currency,
    "hl": "en",
    "adults": adults,
    "children": children,
    "api_key": self.api_key,
}
cabin_map = {"economy": "1", "premium_economy": "2", "business": "3", "first": "4"}
params["travel_class"] = cabin_map.get(cabin_class, "1")
```

**Missing from SerpAPI params**: `stops`, `infants_in_seat`, `infants_on_lap`, `bags`, `include_airlines`, `exclude_airlines`

### 5.2 SkyscannerSource (flight_price_fetcher.py, lines 184-261)

Handles `cabin_class` natively:

```python
params = {
    "cabinClass": cabin_class,  # Passed directly
    "adults": adults,
    "children": children,
}
```

**Missing**: `stops`, `infants_*`, `bags`, airline filters

### 5.3 AmadeusSource (flight_price_fetcher.py, lines 264-365)

Handles cabin class with uppercase mapping:

```python
cabin_map = {"economy": "ECONOMY", "premium_economy": "PREMIUM_ECONOMY",
            "business": "BUSINESS", "first": "FIRST"}
params["travelClass"] = cabin_map.get(cabin_class, "ECONOMY")
```

**Missing**: `stops`, `infants_*`, `bags`, airline filters

### 5.4 Summary: What Each Source Handles

| Parameter | SerpAPI | Skyscanner | Amadeus | Playwright Scraper |
|-----------|---------|------------|---------|-------------------|
| origin/destination | Yes | Yes | Yes | Yes |
| dates | Yes | Yes | Yes | Yes |
| adults | Yes | Yes | Yes | Accepted, not used |
| children | Yes | Yes | Yes | Accepted, not used |
| infants_in_seat | **No** | **No** | **No** | **No** |
| infants_on_lap | **No** | **No** | **No** | **No** |
| cabin_class | Yes | Yes | Yes | **No** |
| stops_filter | **No** | **No** | **No** | **No** |
| include_airlines | **No** | **No** | **No** | **No** |
| exclude_airlines | **No** | **No** | **No** | **No** |
| carry_on_bags | **No** | **No** | **No** | **No** |
| checked_bags | **No** | **No** | **No** | **No** |
| currency | Yes | Yes | Yes | Hardcoded NZD |

---

## 6. Proposed Changes

### 6.1 Strategy: Two-Track Approach

**Track 1 - API Sources (SerpAPI, Skyscanner, Amadeus)**: Pass all SearchDefinition filter parameters through the API source interfaces. These APIs have well-defined parameters and this is straightforward.

**Track 2 - Playwright Scraper**: Use the natural language `q=` URL format (current approach) but **supplement with Playwright UI interactions** to apply filters after page load. This is more reliable than trying to encode protobuf `tfs=` parameters.

**Track 3 - Booking Links**: Enhance the natural language URL with additional context where possible, but accept that the user may need to re-apply some filters after clicking through.

### 6.2 Detailed Proposed Changes

#### A. Update `PriceSource.fetch_prices()` Interface

Add missing parameters to the abstract interface:

```python
@abstractmethod
async def fetch_prices(
    self,
    origin: str,
    destination: str,
    departure_date: date,
    return_date: Optional[date],
    adults: int,
    children: int,
    cabin_class: str,
    currency: str,
    # New parameters:
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    stops: int = 0,  # 0=any, 1=nonstop, 2=one_stop_or_fewer, 3=two_plus
    carry_on_bags: int = 0,
    include_airlines: Optional[str] = None,
    exclude_airlines: Optional[str] = None,
) -> FetchResult:
```

#### B. Update `SerpAPISource.fetch_prices()`

Add the new parameters to the SerpAPI request:

```python
# Stops filter
if stops > 0:
    params["stops"] = stops

# Infant passengers
if infants_in_seat > 0:
    params["infants_in_seat"] = infants_in_seat
if infants_on_lap > 0:
    params["infants_on_lap"] = infants_on_lap

# Bags
if carry_on_bags > 0:
    params["bags"] = carry_on_bags

# Airline filters
if include_airlines:
    params["include_airlines"] = include_airlines
elif exclude_airlines:
    params["exclude_airlines"] = exclude_airlines
```

#### C. Update `GoogleFlightsScraper.scrape_route()` and `_build_url()`

Add all filter parameters to the scraper interface. For the URL, continue using the `q=` format but add `gl=` parameter. For filters, apply them via Playwright interactions after page load:

```python
async def scrape_route(
    self,
    search_definition_id: int,
    origin: str,
    destination: str,
    departure_date: date,
    return_date: Optional[date],
    adults: int = 2,
    children: int = 2,
    # New:
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    cabin_class: str = "economy",
    stops_filter: str = "any",
    currency: str = "NZD",
    carry_on_bags: int = 0,
    checked_bags: int = 0,
) -> ScrapeResult:
```

For `_build_url()`, use the `currency` parameter instead of hardcoding:

```python
def _build_url(self, origin, destination, departure_date, return_date, currency="NZD") -> str:
    # ...
    url += f"&curr={currency}&hl=en&gl=nz"
    return url
```

**Playwright filter application** (new method):

```python
async def _apply_filters(self, page: Page, cabin_class: str, stops_filter: str,
                          adults: int, children: int, infants_in_seat: int,
                          infants_on_lap: int, carry_on_bags: int) -> None:
    """Apply search filters via UI interactions after page load."""
    # This is a Phase 2 enhancement - for now, the URL parameters
    # handle the basic search, and filters can be applied via UI clicks
    # on the Google Flights filter toolbar.
    pass
```

**Note**: Full Playwright UI filter automation is complex and fragile. The recommended Phase 1 approach is to pass all parameters through the API sources (SerpAPI, Skyscanner, Amadeus) and accept that Playwright scraping may not pre-filter. The Playwright results can be post-filtered in Python code.

#### D. Update `build_google_flights_url()` (Template Helper)

Actually use the `cabin_code` that is already computed. Add natural language hints for cabin class and passenger count:

```python
def build_google_flights_url(
    origin: str, destination: str, departure_date: date,
    return_date: Optional[date] = None, adults: int = 1,
    children: int = 0, cabin_class: str = "economy",
    currency: str = "NZD",
    infants_in_seat: int = 0, infants_on_lap: int = 0,
    stops_filter: str = "any",
) -> str:
    dep_str = departure_date.strftime("%Y-%m-%d")
    base = "https://www.google.com/travel/flights"

    # Build natural language query
    query = f"Flights from {origin} to {destination} on {dep_str}"
    if return_date:
        query += f" returning {return_date.strftime('%Y-%m-%d')}"

    # Add cabin class hint to natural language query
    cabin_hints = {
        "premium_economy": " premium economy",
        "business": " business class",
        "first": " first class",
    }
    if cabin_class in cabin_hints:
        query += cabin_hints[cabin_class]

    # Add nonstop hint to natural language query
    if stops_filter == "nonstop":
        query += " nonstop"

    query_parts = [f"q={query}"]
    query_parts.extend([f"curr={currency}", "hl=en", "gl=nz"])

    return f"{base}?{'&'.join(query_parts)}"
```

#### E. Update `TripPlanSearch._build_booking_url()`

Replace with a call to the centralized `build_google_flights_url()` to eliminate code duplication.

#### F. Update `ScrapingService.scrape_search_definition()`

Pass all SearchDefinition fields through to the scraper:

```python
result = await self.scraper.scrape_route(
    search_definition_id=search_def.id,
    origin=search_def.origin,
    destination=search_def.destination,
    departure_date=departure_date,
    return_date=return_date,
    adults=search_def.adults,
    children=search_def.children,
    infants_in_seat=search_def.infants_in_seat,
    infants_on_lap=search_def.infants_on_lap,
    cabin_class=search_def.cabin_class.value,
    stops_filter=search_def.stops_filter.value,
    currency=search_def.currency,
    carry_on_bags=search_def.carry_on_bags,
    checked_bags=search_def.checked_bags,
)
```

### 6.3 StopsFilter Mapping Table

| SearchDefinition StopsFilter | SerpAPI `stops` | Natural Language Hint | Playwright UI |
|-----------------------------|-----------------|-----------------------|---------------|
| `ANY` | `0` | (none) | (default) |
| `NONSTOP` | `1` | "nonstop" | Click "Stops" -> "Nonstop only" |
| `ONE_STOP` | `2` | "1 stop or fewer" | Click "Stops" -> "1 stop or fewer" |
| `TWO_PLUS` | `3` | "2 stops or fewer" | Click "Stops" -> "2 stops or fewer" |

### 6.4 CabinClass Mapping Table

| SearchDefinition CabinClass | SerpAPI `travel_class` | NL Hint | Amadeus | Skyscanner |
|----------------------------|----------------------|---------|---------|------------|
| `ECONOMY` | `1` | (none) | `ECONOMY` | `economy` |
| `PREMIUM_ECONOMY` | `2` | "premium economy" | `PREMIUM_ECONOMY` | `premium_economy` |
| `BUSINESS` | `3` | "business class" | `BUSINESS` | `business` |
| `FIRST` | `4` | "first class" | `FIRST` | `first` |

---

## 7. Files That Need Changes

### Primary Changes

| File | Change | Priority |
|------|--------|----------|
| `backend/app/scrapers/google_flights.py` | Update `_build_url()` and `scrape_route()` signatures to accept and use all filter params | P1 |
| `backend/app/utils/template_helpers.py` | Fix `build_google_flights_url()` to actually use computed `cabin_code`, add stops hint, use currency param | P1 |
| `backend/app/services/scraping_service.py` | Pass all SearchDefinition fields to scraper | P1 |
| `backend/app/services/flight_price_fetcher.py` | Update `PriceSource` abstract interface and all source implementations to pass stops, infants, bags, airlines | P1 |
| `backend/app/services/trip_plan_search.py` | Replace `_build_booking_url()` with call to centralized `build_google_flights_url()` | P2 |

### Secondary Changes (Callers)

| File | Change | Priority |
|------|--------|----------|
| `backend/app/api/prices.py` | Pass `stops_filter`, `infants_*`, `bags` to `build_google_flights_url()` | P2 |
| `backend/celery_app/tasks/scrape_flights.py` | Update legacy `scrape_route()` call to pass new params (this file uses old Route model) | P3 |

### Testing

| File | Change | Priority |
|------|--------|----------|
| New: `backend/tests/test_url_builder.py` | Unit tests for URL construction with all parameter combinations | P1 |
| Existing scraper tests | Update to verify new parameters are passed through | P2 |

---

## 8. Risk Assessment

### Low Risk
- Updating `build_google_flights_url()` to include natural language hints (nonstop, business class) -- Google's NL parser handles these well
- Passing new params through SerpAPI, Skyscanner, Amadeus -- these APIs have documented support
- Using `currency` from SearchDefinition instead of hardcoding NZD

### Medium Risk
- Natural language cabin/stops hints may not always be parsed correctly by Google
- Airline filter passthrough depends on correct IATA codes in the database

### High Risk (Defer)
- Protobuf `tfs=` encoding for direct Google Flights URLs -- undocumented, fragile, may break
- Full Playwright UI automation for filter application -- complex, maintenance-heavy
- Checked bags filter -- not supported by SerpAPI or Google Flights URL params directly

### Recommended Phase 1 Scope
1. Pass all parameters through API sources (SerpAPI, Skyscanner, Amadeus)
2. Fix `build_google_flights_url()` to use its already-computed `cabin_code` and add NL hints
3. Centralize URL building (eliminate `_build_booking_url()` duplication)
4. Use `currency` from SearchDefinition everywhere
5. Add `gl=nz` parameter for geolocation consistency
6. Post-filter Playwright results in Python if stops/cabin don't match

### Defer to Phase 2
- Protobuf `tfs=` URL encoding
- Playwright UI filter automation
- Currency verification after page load
- Checked bags filter (not supported by APIs)
