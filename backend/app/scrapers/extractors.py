"""
Multi-fallback extraction strategies for Google Flights scraping.

This module implements 20+ fallback strategies for extracting flight data,
with validation at every step to ensure data quality.

Principles:
1. Try specific selectors first (fastest)
2. Fall back to broader patterns
3. Validate all extracted data
4. Log which strategy succeeded
5. Never fail completely - extract what we can
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
from playwright.async_api import Page, ElementHandle

logger = logging.getLogger(__name__)


# =============================================================================
# Validation Rules
# =============================================================================

@dataclass
class ValidationResult:
    """Result of validating extracted data."""
    is_valid: bool
    value: Any
    confidence: float  # 0.0 to 1.0
    reason: str = ""
    fallback_level: int = 0  # Which fallback strategy succeeded (0 = primary)


class PriceValidator:
    """Validate extracted prices."""

    MIN_PRICE = 50       # Minimum reasonable flight price
    MAX_PRICE = 50000    # Maximum reasonable flight price

    # Suspicious prices that are likely UI elements, not flight prices
    SUSPICIOUS_PRICES = {1, 2, 3, 4, 5, 10, 100, 1000, 10000}

    @classmethod
    def validate(cls, price: int, context: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate a price value.

        Args:
            price: The extracted price in currency units
            context: Optional context (route, typical prices, etc.)

        Returns:
            ValidationResult with validity and confidence
        """
        if price < cls.MIN_PRICE:
            return ValidationResult(
                is_valid=False,
                value=price,
                confidence=0.0,
                reason=f"Price {price} below minimum {cls.MIN_PRICE}"
            )

        if price > cls.MAX_PRICE:
            return ValidationResult(
                is_valid=False,
                value=price,
                confidence=0.0,
                reason=f"Price {price} above maximum {cls.MAX_PRICE}"
            )

        if price in cls.SUSPICIOUS_PRICES:
            return ValidationResult(
                is_valid=False,
                value=price,
                confidence=0.1,
                reason=f"Price {price} is suspiciously round"
            )

        # Calculate confidence based on price range
        # Typical international flights: 300-5000
        if 200 <= price <= 8000:
            confidence = 0.95
        elif 100 <= price <= 15000:
            confidence = 0.8
        else:
            confidence = 0.6

        return ValidationResult(
            is_valid=True,
            value=price,
            confidence=confidence,
            reason="Price within expected range"
        )


class AirlineValidator:
    """Validate extracted airline names."""

    # Known airlines (subset - expand as needed)
    KNOWN_AIRLINES = {
        # Major international
        "air new zealand", "qantas", "virgin australia", "jetstar",
        "singapore airlines", "cathay pacific", "emirates", "qatar airways",
        "united", "american airlines", "delta", "lufthansa", "british airways",
        "air france", "klm", "ana", "jal", "korean air", "thai airways",
        "malaysia airlines", "garuda indonesia", "philippine airlines",
        "china eastern", "china southern", "air china", "eva air",
        "fiji airways", "hawaiian airlines", "alaska airlines",
        # Low-cost carriers
        "airasia", "scoot", "cebu pacific", "spring airlines",
        "indigo", "spicejet", "lion air", "vietjet",
    }

    # Patterns that indicate airline names
    AIRLINE_PATTERNS = [
        r"(?:air|airlines?|airways?)\b",
        r"\b(?:fly|jet|star)\b",
    ]

    @classmethod
    def validate(cls, airline: str) -> ValidationResult:
        """Validate an airline name."""
        if not airline or airline.lower() == "unknown":
            return ValidationResult(
                is_valid=False,
                value=airline,
                confidence=0.0,
                reason="Empty or unknown airline"
            )

        airline_lower = airline.lower().strip()

        # Check known airlines
        if airline_lower in cls.KNOWN_AIRLINES:
            return ValidationResult(
                is_valid=True,
                value=airline,
                confidence=0.95,
                reason="Known airline"
            )

        # Check partial matches
        for known in cls.KNOWN_AIRLINES:
            if known in airline_lower or airline_lower in known:
                return ValidationResult(
                    is_valid=True,
                    value=airline,
                    confidence=0.85,
                    reason=f"Partial match with {known}"
                )

        # Check patterns
        for pattern in cls.AIRLINE_PATTERNS:
            if re.search(pattern, airline_lower):
                return ValidationResult(
                    is_valid=True,
                    value=airline,
                    confidence=0.7,
                    reason="Matches airline pattern"
                )

        # Unknown but could still be valid
        if 2 <= len(airline) <= 50:
            return ValidationResult(
                is_valid=True,
                value=airline,
                confidence=0.5,
                reason="Unknown airline, reasonable length"
            )

        return ValidationResult(
            is_valid=False,
            value=airline,
            confidence=0.1,
            reason="Does not match airline patterns"
        )


class StopsValidator:
    """Validate number of stops."""

    MAX_STOPS = 4  # More than 4 stops is unrealistic

    @classmethod
    def validate(cls, stops: int, duration_minutes: int = 0) -> ValidationResult:
        """
        Validate stops count.

        Args:
            stops: Number of stops
            duration_minutes: Flight duration (for cross-validation)
        """
        if stops < 0:
            return ValidationResult(
                is_valid=False,
                value=stops,
                confidence=0.0,
                reason="Negative stops not possible"
            )

        if stops > cls.MAX_STOPS:
            return ValidationResult(
                is_valid=False,
                value=stops,
                confidence=0.0,
                reason=f"More than {cls.MAX_STOPS} stops unrealistic"
            )

        # Cross-validate with duration if available
        if duration_minutes > 0:
            # Rough heuristic: each stop adds ~2-4 hours
            min_duration_for_stops = stops * 90  # At least 1.5h per stop
            if duration_minutes < min_duration_for_stops and stops > 0:
                return ValidationResult(
                    is_valid=True,
                    value=stops,
                    confidence=0.6,
                    reason="Duration seems short for stops count"
                )

        return ValidationResult(
            is_valid=True,
            value=stops,
            confidence=0.9,
            reason="Valid stops count"
        )


class DurationValidator:
    """Validate flight duration."""

    MIN_DURATION = 30      # 30 minutes minimum
    MAX_DURATION = 48 * 60  # 48 hours maximum

    @classmethod
    def validate(cls, duration_minutes: int) -> ValidationResult:
        """Validate duration in minutes."""
        if duration_minutes < cls.MIN_DURATION:
            return ValidationResult(
                is_valid=False,
                value=duration_minutes,
                confidence=0.0,
                reason=f"Duration {duration_minutes}m below minimum {cls.MIN_DURATION}m"
            )

        if duration_minutes > cls.MAX_DURATION:
            return ValidationResult(
                is_valid=False,
                value=duration_minutes,
                confidence=0.0,
                reason=f"Duration {duration_minutes}m above maximum {cls.MAX_DURATION}m"
            )

        # Most flights are 1-24 hours
        if 60 <= duration_minutes <= 24 * 60:
            confidence = 0.95
        else:
            confidence = 0.7

        return ValidationResult(
            is_valid=True,
            value=duration_minutes,
            confidence=confidence,
            reason="Valid duration"
        )


# =============================================================================
# Extraction Strategies
# =============================================================================

@dataclass
class ExtractionResult:
    """Result of an extraction attempt."""
    success: bool
    value: Any
    confidence: float
    strategy_name: str
    fallback_level: int
    raw_text: str = ""
    validation: Optional[ValidationResult] = None


class PriceExtractor:
    """
    Extract prices with 20+ fallback strategies.

    Strategy hierarchy:
    1. Data attributes (most reliable)
    2. ARIA labels (accessibility, usually accurate)
    3. Specific CSS classes (may change)
    4. Jsname attributes (Google's internal)
    5. Structural patterns (generic but stable)
    6. Text pattern matching (last resort)
    """

    # 20+ extraction strategies in priority order
    STRATEGIES = [
        # Level 0: Data attributes (most reliable)
        {"name": "data-gs", "selector": "[data-gs]", "level": 0},
        {"name": "data-price", "selector": "[data-price]", "level": 0},
        {"name": "data-value", "selector": "[data-value]", "level": 0},

        # Level 1: ARIA labels (accessibility, usually accurate)
        {"name": "aria-dollars", "selector": "span[aria-label*='dollars']", "level": 1},
        {"name": "aria-nzd", "selector": "span[aria-label*='NZD']", "level": 1},
        {"name": "aria-aud", "selector": "span[aria-label*='AUD']", "level": 1},
        {"name": "aria-price", "selector": "[aria-label*='price']", "level": 1},
        {"name": "aria-cost", "selector": "[aria-label*='cost']", "level": 1},

        # Level 2: Known CSS classes (may change with Google updates)
        {"name": "class-YMlIz", "selector": ".YMlIz", "level": 2},
        {"name": "class-price", "selector": "[class*='price']", "level": 2},
        {"name": "class-amount", "selector": "[class*='amount']", "level": 2},
        {"name": "class-fare", "selector": "[class*='fare']", "level": 2},

        # Level 3: Jsname attributes (Google's internal naming)
        {"name": "jsname-IWWDBc", "selector": "[jsname='IWWDBc']", "level": 3},
        {"name": "jsname-price", "selector": "[jsname*='rice']", "level": 3},

        # Level 4: Structural patterns (generic but stable)
        {"name": "div-price-span", "selector": "div[class*='price'] span", "level": 4},
        {"name": "span-currency", "selector": "span:has-text('$')", "level": 4},
        {"name": "price-container", "selector": "[class*='result'] [class*='price']", "level": 4},
        {"name": "flight-card-price", "selector": "[class*='flight'] [class*='price']", "level": 4},

        # Level 5: Text pattern matching (last resort)
        {"name": "text-nzd", "selector": "text=/NZ\\$\\d+/", "level": 5},
        {"name": "text-dollar", "selector": "text=/\\$\\d{3,}/", "level": 5},
        {"name": "all-spans", "selector": "span", "level": 5},  # Scan all spans
    ]

    # Price extraction regex patterns
    PRICE_PATTERNS = [
        (r'NZ\$\s*([\d,]+)', "NZD prefix"),
        (r'AU\$\s*([\d,]+)', "AUD prefix"),
        (r'\$\s*([\d,]+)', "Dollar prefix"),
        (r'([\d,]+)\s*NZD', "NZD suffix"),
        (r'([\d,]+)\s*AUD', "AUD suffix"),
        (r'€\s*([\d,]+)', "Euro"),
        (r'£\s*([\d,]+)', "Pound"),
        # Bare number regex REMOVED -- was matching flight numbers, seat IDs,
        # and other non-price numbers. Emergency fallback is now only used
        # within RowExtractor for elements with price-context indicators.
    ]

    # Emergency fallback: only used within per-row extraction for elements
    # that have price-related ARIA labels or class names
    EMERGENCY_PRICE_PATTERN = (r'\b(\d{3,5})\b', "Bare number (emergency)")

    @classmethod
    async def extract(cls, page: Page) -> List[ExtractionResult]:
        """
        Extract all prices from the page using fallback strategies.

        Returns list of ExtractionResults sorted by confidence.
        """
        results = []
        seen_prices = set()

        for strategy in cls.STRATEGIES:
            try:
                elements = await page.query_selector_all(strategy["selector"])

                for element in elements[:50]:  # Limit per strategy
                    try:
                        extraction = await cls._extract_from_element(
                            element,
                            strategy["name"],
                            strategy["level"]
                        )

                        if extraction and extraction.success:
                            price = extraction.value
                            if price not in seen_prices:
                                seen_prices.add(price)
                                results.append(extraction)
                                logger.debug(
                                    f"Price {price} extracted via {strategy['name']} "
                                    f"(level {strategy['level']}, confidence {extraction.confidence:.2f})"
                                )
                    except Exception as e:
                        logger.debug(f"Element extraction failed: {e}")
                        continue

            except Exception as e:
                logger.debug(f"Strategy {strategy['name']} failed: {e}")
                continue

        # Sort by confidence (highest first)
        results.sort(key=lambda x: x.confidence, reverse=True)

        # Log summary
        if results:
            logger.info(
                f"Extracted {len(results)} prices. "
                f"Best: ${results[0].value} via {results[0].strategy_name} "
                f"(confidence {results[0].confidence:.2f})"
            )
        else:
            logger.warning("No prices extracted from any strategy")

        return results

    @classmethod
    async def _extract_from_element(
        cls,
        element: ElementHandle,
        strategy_name: str,
        level: int
    ) -> Optional[ExtractionResult]:
        """Extract price from a single element."""
        # Get text content
        text = await element.inner_text() or ""

        # Also check aria-label
        aria = await element.get_attribute("aria-label") or ""

        # Check data attributes
        data_price = await element.get_attribute("data-price")
        data_value = await element.get_attribute("data-value")
        data_gs = await element.get_attribute("data-gs")

        combined_text = f"{text} {aria} {data_price or ''} {data_value or ''} {data_gs or ''}"

        # Try each pattern
        for pattern, pattern_name in cls.PRICE_PATTERNS:
            match = re.search(pattern, combined_text.replace(',', ''))
            if match:
                try:
                    price = int(match.group(1).replace(',', ''))

                    # Validate
                    validation = PriceValidator.validate(price)

                    if validation.is_valid:
                        # Adjust confidence based on extraction level
                        level_penalty = level * 0.05  # Lower levels are more reliable
                        confidence = min(validation.confidence - level_penalty, 0.99)

                        return ExtractionResult(
                            success=True,
                            value=price,
                            confidence=confidence,
                            strategy_name=strategy_name,
                            fallback_level=level,
                            raw_text=combined_text[:100],
                            validation=validation
                        )
                except ValueError:
                    continue

        return None


class FlightDetailsExtractor:
    """
    Extract airline, stops, and duration with 10+ fallback strategies each.
    """

    # Airline extraction strategies
    AIRLINE_STRATEGIES = [
        {"name": "aria-airline", "selector": "[aria-label*='airline']", "level": 0},
        {"name": "aria-operated", "selector": "[aria-label*='Operated by']", "level": 0},
        {"name": "data-carrier", "selector": "[data-carrier]", "level": 0},
        {"name": "class-carrier", "selector": "[class*='carrier']", "level": 1},
        {"name": "class-airline", "selector": "[class*='airline']", "level": 1},
        {"name": "img-airline", "selector": "img[alt*='airline'], img[alt*='Airways']", "level": 2},
        {"name": "span-airline", "selector": "span[class*='operator']", "level": 2},
        {"name": "flight-row", "selector": "[class*='flight'] [class*='name']", "level": 3},
        {"name": "leg-carrier", "selector": "[class*='leg'] [class*='carrier']", "level": 3},
        {"name": "itinerary-airline", "selector": "[class*='itinerary'] img[alt]", "level": 4},
    ]

    # Stops extraction strategies
    STOPS_STRATEGIES = [
        {"name": "aria-stops", "selector": "[aria-label*='stop']", "level": 0},
        {"name": "aria-nonstop", "selector": "[aria-label*='Nonstop']", "level": 0},
        {"name": "aria-direct", "selector": "[aria-label*='direct']", "level": 0},
        {"name": "class-stops", "selector": "[class*='stop']", "level": 1},
        {"name": "data-stops", "selector": "[data-stops]", "level": 1},
        {"name": "text-stop", "selector": "text=/\\d+\\s*stop/i", "level": 2},
        {"name": "text-nonstop", "selector": "text=/nonstop|non-stop|direct/i", "level": 2},
        {"name": "layover", "selector": "[class*='layover']", "level": 3},
        {"name": "connection", "selector": "[class*='connection']", "level": 3},
        {"name": "via-text", "selector": "text=/via\\s+\\w+/i", "level": 4},
    ]

    # Duration extraction strategies
    DURATION_STRATEGIES = [
        {"name": "aria-duration", "selector": "[aria-label*='duration']", "level": 0},
        {"name": "aria-hours", "selector": "[aria-label*='hr'], [aria-label*='hour']", "level": 0},
        {"name": "data-duration", "selector": "[data-duration]", "level": 0},
        {"name": "class-duration", "selector": "[class*='duration']", "level": 1},
        {"name": "class-time", "selector": "[class*='total-time'], [class*='travel-time']", "level": 1},
        {"name": "text-hr-min", "selector": "text=/\\d+\\s*h(r|our)?\\s*\\d*\\s*m/i", "level": 2},
        {"name": "text-hours", "selector": "text=/\\d+\\s*hours?/i", "level": 2},
        {"name": "time-span", "selector": "[class*='flight'] [class*='time']", "level": 3},
        {"name": "leg-duration", "selector": "[class*='leg'] [class*='duration']", "level": 3},
        {"name": "itinerary-time", "selector": "[class*='itinerary'] [class*='time']", "level": 4},
    ]

    # Duration parsing patterns
    DURATION_PATTERNS = [
        (r'(\d+)\s*h(?:r|our)?s?\s*(\d+)\s*m(?:in)?', "hours and minutes"),
        (r'(\d+)\s*h(?:r|our)?s?', "hours only"),
        (r'(\d+)\s*m(?:in(?:ute)?s?)?', "minutes only"),
        (r'(\d{1,2}):(\d{2})', "HH:MM format"),
    ]

    # Stops parsing patterns
    STOPS_PATTERNS = [
        (r'(\d+)\s*stop', "N stops"),
        (r'nonstop|non-stop|direct', "nonstop"),
    ]

    @classmethod
    async def extract_airline(cls, page: Page) -> List[ExtractionResult]:
        """Extract airline names from page."""
        results = []
        seen = set()

        for strategy in cls.AIRLINE_STRATEGIES:
            try:
                elements = await page.query_selector_all(strategy["selector"])

                for element in elements[:20]:
                    try:
                        text = await element.inner_text() or ""
                        aria = await element.get_attribute("aria-label") or ""
                        alt = await element.get_attribute("alt") or ""

                        combined = f"{text} {aria} {alt}".strip()

                        # Clean up the airline name
                        airline = cls._clean_airline_name(combined)

                        if airline and airline.lower() not in seen:
                            seen.add(airline.lower())

                            validation = AirlineValidator.validate(airline)

                            if validation.is_valid:
                                level_penalty = strategy["level"] * 0.05
                                confidence = max(validation.confidence - level_penalty, 0.1)

                                results.append(ExtractionResult(
                                    success=True,
                                    value=airline,
                                    confidence=confidence,
                                    strategy_name=strategy["name"],
                                    fallback_level=strategy["level"],
                                    raw_text=combined[:100],
                                    validation=validation
                                ))
                    except Exception:
                        continue
            except Exception:
                continue

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    @classmethod
    def _clean_airline_name(cls, text: str) -> Optional[str]:
        """Clean and extract airline name from text."""
        if not text:
            return None

        # Remove common prefixes
        text = re.sub(r'^(Operated by|Marketed by|Flights? on)\s*', '', text, flags=re.I)

        # Remove flight numbers
        text = re.sub(r'\b[A-Z]{2}\d+\b', '', text)

        # Remove times
        text = re.sub(r'\d{1,2}:\d{2}(\s*(AM|PM))?', '', text, flags=re.I)

        # Clean whitespace
        text = ' '.join(text.split()).strip()

        # Check reasonable length
        if 2 <= len(text) <= 50:
            return text

        return None

    @classmethod
    async def extract_stops(cls, page: Page) -> List[ExtractionResult]:
        """Extract stops count from page."""
        results = []

        for strategy in cls.STOPS_STRATEGIES:
            try:
                elements = await page.query_selector_all(strategy["selector"])

                for element in elements[:20]:
                    try:
                        text = await element.inner_text() or ""
                        aria = await element.get_attribute("aria-label") or ""

                        combined = f"{text} {aria}".lower()

                        # Check for nonstop
                        if re.search(r'nonstop|non-stop|direct', combined):
                            validation = StopsValidator.validate(0)
                            results.append(ExtractionResult(
                                success=True,
                                value=0,
                                confidence=0.95 - strategy["level"] * 0.05,
                                strategy_name=strategy["name"],
                                fallback_level=strategy["level"],
                                raw_text=combined[:50],
                                validation=validation
                            ))
                            continue

                        # Check for N stops
                        match = re.search(r'(\d+)\s*stop', combined)
                        if match:
                            stops = int(match.group(1))
                            validation = StopsValidator.validate(stops)

                            if validation.is_valid:
                                results.append(ExtractionResult(
                                    success=True,
                                    value=stops,
                                    confidence=validation.confidence - strategy["level"] * 0.05,
                                    strategy_name=strategy["name"],
                                    fallback_level=strategy["level"],
                                    raw_text=combined[:50],
                                    validation=validation
                                ))
                    except Exception:
                        continue
            except Exception:
                continue

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    @classmethod
    async def extract_duration(cls, page: Page) -> List[ExtractionResult]:
        """Extract flight duration from page."""
        results = []

        for strategy in cls.DURATION_STRATEGIES:
            try:
                elements = await page.query_selector_all(strategy["selector"])

                for element in elements[:20]:
                    try:
                        text = await element.inner_text() or ""
                        aria = await element.get_attribute("aria-label") or ""

                        combined = f"{text} {aria}"

                        duration = cls._parse_duration(combined)

                        if duration:
                            validation = DurationValidator.validate(duration)

                            if validation.is_valid:
                                results.append(ExtractionResult(
                                    success=True,
                                    value=duration,
                                    confidence=validation.confidence - strategy["level"] * 0.05,
                                    strategy_name=strategy["name"],
                                    fallback_level=strategy["level"],
                                    raw_text=combined[:50],
                                    validation=validation
                                ))
                    except Exception:
                        continue
            except Exception:
                continue

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results

    @classmethod
    def _parse_duration(cls, text: str) -> Optional[int]:
        """Parse duration text to minutes."""
        if not text:
            return None

        # Try hours and minutes: "5h 30m", "5 hr 30 min", etc.
        match = re.search(r'(\d+)\s*h(?:r|our)?s?\s*(\d+)\s*m', text, re.I)
        if match:
            return int(match.group(1)) * 60 + int(match.group(2))

        # Try hours only: "5h", "5 hours"
        match = re.search(r'(\d+)\s*h(?:r|our)?s?(?!\s*\d)', text, re.I)
        if match:
            return int(match.group(1)) * 60

        # Try HH:MM format
        match = re.search(r'(\d{1,2}):(\d{2})', text)
        if match:
            hours, mins = int(match.group(1)), int(match.group(2))
            if hours < 48 and mins < 60:  # Sanity check
                return hours * 60 + mins

        return None


# =============================================================================
# Per-Row Extraction (correlated field extraction)
# =============================================================================

class FlightRowLocator:
    """
    Finds individual flight row containers on the page using multi-level fallback.

    Each row should contain a price, airline, stops, and duration for a single flight.
    The key insight: extracting fields from the same DOM parent ensures they belong
    to the same flight, eliminating the index-matching bug.
    """

    # Row locator strategies in priority order
    ROW_STRATEGIES = [
        # Level 0: Specific Google Flights selectors
        {"name": "yR1fYc", "selector": "li.yR1fYc", "level": 0},
        {"name": "pIav2d", "selector": "li[class*='pIav2d']", "level": 0},

        # Level 1: Category-scoped row discovery
        {"name": "Rk10dc-children", "selector": ".Rk10dc > div", "level": 1},
        {"name": "result-list-item", "selector": "[class*='result'] li", "level": 1},

        # Level 2: ARIA-based (more stable across DOM changes)
        {"name": "aria-listitem", "selector": "[role='listitem']", "level": 2},
        {"name": "aria-row", "selector": "[role='row']", "level": 2},

        # Level 3: DOM traversal from price elements
        {"name": "price-ancestor", "selector": None, "level": 3},  # Special handling
    ]

    # Minimum requirements for a valid flight row
    PRICE_INDICATORS = [
        "[aria-label*='dollar']", "[aria-label*='NZD']", "[aria-label*='price']",
        "[class*='price']", "[data-price]", "span:has-text('$')",
    ]

    AIRLINE_INDICATORS = [
        "[class*='carrier']", "[class*='airline']", "img[alt]",
        "[aria-label*='airline']", "[data-carrier]",
    ]

    @classmethod
    async def find_rows(cls, page: Page) -> Tuple[List[ElementHandle], str, int]:
        """
        Find flight row containers on the page.

        Returns:
            Tuple of (row_elements, strategy_name, strategy_level)
        """
        for strategy in cls.ROW_STRATEGIES:
            if strategy["selector"] is None:
                # Level 3: DOM traversal from price elements
                rows = await cls._find_rows_by_price_traversal(page)
                if rows:
                    logger.info(
                        f"FlightRowLocator: found {len(rows)} rows via "
                        f"price-ancestor traversal (level 3)"
                    )
                    return rows, strategy["name"], strategy["level"]
                continue

            try:
                elements = await page.query_selector_all(strategy["selector"])

                # Filter to elements that look like flight rows
                valid_rows = []
                for el in elements[:30]:  # Cap to prevent scanning too many
                    if await cls._is_valid_flight_row(el):
                        valid_rows.append(el)

                if valid_rows:
                    logger.info(
                        f"FlightRowLocator: found {len(valid_rows)} rows via "
                        f"{strategy['name']} (level {strategy['level']})"
                    )
                    return valid_rows, strategy["name"], strategy["level"]

            except Exception as e:
                logger.debug(f"FlightRowLocator strategy {strategy['name']} failed: {e}")
                continue

        logger.warning("FlightRowLocator: no flight rows found by any strategy")
        return [], "", -1

    @classmethod
    async def _is_valid_flight_row(cls, element: ElementHandle) -> bool:
        """Check if an element looks like a flight row (has price indicator)."""
        for selector in cls.PRICE_INDICATORS:
            try:
                found = await element.query_selector(selector)
                if found:
                    return True
            except Exception:
                continue
        return False

    @classmethod
    async def _find_rows_by_price_traversal(cls, page: Page) -> List[ElementHandle]:
        """
        Level 3 fallback: find price elements, walk up to common ancestor.

        Strategy: find all price-containing elements, then for each,
        walk up the DOM tree to find a reasonable container that also
        has airline/stops info.
        """
        rows = []
        seen_row_ids = set()

        # Find price elements first
        price_selectors = [
            "[aria-label*='dollar']", "[aria-label*='NZD']",
            "[class*='price'] span", "[data-price]",
        ]

        for selector in price_selectors:
            try:
                price_elements = await page.query_selector_all(selector)
                for price_el in price_elements[:20]:
                    # Walk up to find a row-like container
                    row = await cls._find_row_ancestor(price_el)
                    if row:
                        # Deduplicate by checking if we've already found this row
                        row_text = await row.inner_text() or ""
                        row_id = hash(row_text[:200])
                        if row_id not in seen_row_ids:
                            seen_row_ids.add(row_id)
                            rows.append(row)
            except Exception:
                continue

        return rows

    @classmethod
    async def _find_row_ancestor(cls, element: ElementHandle) -> Optional[ElementHandle]:
        """Walk up from a price element to find the flight row container."""
        current = element

        for _ in range(6):  # Walk up max 6 levels
            try:
                parent = await current.evaluate_handle("el => el.parentElement")
                if not parent:
                    break

                # Check if this parent has both price and airline indicators
                has_airline = False
                for selector in cls.AIRLINE_INDICATORS:
                    try:
                        found = await parent.as_element().query_selector(selector)
                        if found:
                            has_airline = True
                            break
                    except Exception:
                        continue

                if has_airline:
                    return parent.as_element()

                current = parent.as_element()
            except Exception:
                break

        return None


class RowExtractor:
    """
    Extracts price, airline, stops, and duration from a single flight row element.

    This is the core of the per-row extraction fix. By scoping all queries to
    a single row element, we guarantee that extracted fields belong to the same flight.
    """

    @classmethod
    async def extract_from_row(
        cls,
        row: ElementHandle,
        row_strategy: str,
        row_level: int,
    ) -> Optional['FlightData']:
        """
        Extract a FlightData from a single row element.

        Returns None if no price can be extracted (price is required).
        """
        # Extract price (required)
        price_result = await cls._extract_price(row)
        if not price_result:
            return None

        # Extract optional fields
        airline_result = await cls._extract_airline(row)
        stops_result = await cls._extract_stops(row)
        duration_result = await cls._extract_duration(row)

        # Determine correlation confidence based on row discovery method
        correlation = cls._correlation_for_level(row_level)

        flight = FlightData(
            price=price_result.value,
            price_confidence=price_result.confidence,
            price_strategy=price_result.strategy_name,
            extraction_method="per_row",
            correlation_confidence=correlation,
        )

        if airline_result:
            flight.airline = airline_result.value
            flight.airline_confidence = airline_result.confidence
            flight.airline_strategy = airline_result.strategy_name

        if stops_result:
            flight.stops = stops_result.value
            flight.stops_confidence = stops_result.confidence
            flight.stops_strategy = stops_result.strategy_name

        if duration_result:
            flight.duration_minutes = duration_result.value
            flight.duration_confidence = duration_result.confidence
            flight.duration_strategy = duration_result.strategy_name

        flight.calculate_overall_confidence()

        flight.extraction_summary = {
            "price_strategy": price_result.strategy_name,
            "price_level": price_result.fallback_level,
            "airline_extracted": flight.airline is not None,
            "stops_extracted": flight.stops is not None,
            "duration_extracted": flight.duration_minutes is not None,
            "extraction_method": "per_row",
            "correlation_confidence": correlation,
            "row_strategy": row_strategy,
        }

        return flight

    @staticmethod
    def _correlation_for_level(level: int) -> float:
        """Map row locator level to correlation confidence."""
        return {
            0: 0.95,  # Specific Google Flights selectors
            1: 0.90,  # Category-scoped rows
            2: 0.90,  # ARIA-based rows
            3: 0.80,  # DOM traversal from price elements
        }.get(level, 0.70)

    @classmethod
    async def _extract_price(cls, row: ElementHandle) -> Optional[ExtractionResult]:
        """Extract price from within a row element."""
        # Try row-scoped price selectors (use standard PRICE_PATTERNS)
        price_selectors = [
            ("[data-price]", 0),
            ("[aria-label*='dollar']", 1),
            ("[aria-label*='NZD']", 1),
            ("[aria-label*='price']", 1),
            ("[class*='price'] span", 2),
            (".U3gSDe .FpEdX span", 2),  # Known Google Flights price container
            ("[class*='price']", 2),
        ]

        for selector, level in price_selectors:
            try:
                elements = await row.query_selector_all(selector)
                for element in elements[:10]:
                    result = await PriceExtractor._extract_from_element(
                        element, f"row_{selector}", level
                    )
                    if result and result.success:
                        return result
            except Exception:
                continue

        # Emergency fallback: try bare number pattern ONLY on elements
        # that have price-context indicators (ARIA labels, class names)
        return await cls._extract_price_emergency(row)

    # Month names used to detect date context around bare numbers
    _MONTH_PATTERN = re.compile(
        r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?'
        r'|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?'
        r'|Dec(?:ember)?)\b',
        re.IGNORECASE,
    )

    @classmethod
    def _looks_like_year_in_date(cls, number: int, text: str) -> bool:
        """
        Return True if `number` appears to be a calendar year inside date text.

        A bare number in the 2020-2035 range is likely a year when the
        surrounding text contains month names (e.g. "Mar 15, 2026").
        Legitimate prices at $2026 would have been caught earlier by
        currency-symbol patterns ($, NZ$, etc.) and never reach the
        emergency fallback.
        """
        if not (2020 <= number <= 2035):
            return False
        return bool(cls._MONTH_PATTERN.search(text))

    @classmethod
    async def _extract_price_emergency(cls, row: ElementHandle) -> Optional[ExtractionResult]:
        """
        Emergency price extraction using bare number pattern.

        Only applied to elements within the row that have price-related
        ARIA labels or class names, to avoid matching flight numbers.
        """
        price_context_selectors = [
            "[aria-label*='dollar']", "[aria-label*='price']",
            "[aria-label*='cost']", "[aria-label*='fare']",
            "[class*='price']", "[class*='fare']", "[class*='cost']",
        ]

        pattern, pattern_name = PriceExtractor.EMERGENCY_PRICE_PATTERN

        for selector in price_context_selectors:
            try:
                elements = await row.query_selector_all(selector)
                for element in elements[:5]:
                    text = await element.inner_text() or ""
                    aria = await element.get_attribute("aria-label") or ""
                    combined = f"{text} {aria}"
                    combined_clean = combined.replace(',', '')

                    match = re.search(pattern, combined_clean)
                    if match:
                        try:
                            price = int(match.group(1))

                            # Skip bare numbers that look like years in date text
                            if cls._looks_like_year_in_date(price, combined):
                                logger.debug(
                                    f"Emergency fallback: skipping {price} — "
                                    f"looks like year in date context: {combined[:80]}"
                                )
                                continue

                            validation = PriceValidator.validate(price)
                            if validation.is_valid:
                                return ExtractionResult(
                                    success=True,
                                    value=price,
                                    confidence=max(validation.confidence - 0.15, 0.3),
                                    strategy_name=f"row_emergency_{selector}",
                                    fallback_level=5,
                                    raw_text=combined[:100],
                                    validation=validation,
                                )
                        except ValueError:
                            continue
            except Exception:
                continue

        return None

    @classmethod
    async def _extract_airline(cls, row: ElementHandle) -> Optional[ExtractionResult]:
        """Extract airline from within a row element."""
        selectors = [
            ("[data-carrier]", 0),
            ("[aria-label*='airline']", 0),
            ("[aria-label*='Operated by']", 0),
            ("[class*='carrier']", 1),
            ("[class*='airline']", 1),
            ("img[alt*='Airways']", 2),
            ("img[alt*='Airlines']", 2),
            ("img[alt*='Air']", 2),
            ("img[alt]", 3),
        ]

        for selector, level in selectors:
            try:
                elements = await row.query_selector_all(selector)
                for element in elements[:5]:
                    text = await element.inner_text() or ""
                    aria = await element.get_attribute("aria-label") or ""
                    alt = await element.get_attribute("alt") or ""

                    combined = f"{text} {aria} {alt}".strip()
                    airline = FlightDetailsExtractor._clean_airline_name(combined)

                    if airline:
                        validation = AirlineValidator.validate(airline)
                        if validation.is_valid:
                            level_penalty = level * 0.05
                            return ExtractionResult(
                                success=True,
                                value=airline,
                                confidence=max(validation.confidence - level_penalty, 0.1),
                                strategy_name=f"row_{selector}",
                                fallback_level=level,
                                raw_text=combined[:100],
                                validation=validation,
                            )
            except Exception:
                continue

        return None

    @classmethod
    async def _extract_stops(cls, row: ElementHandle) -> Optional[ExtractionResult]:
        """Extract stops count from within a row element."""
        selectors = [
            ("[aria-label*='stop']", 0),
            ("[aria-label*='Nonstop']", 0),
            ("[aria-label*='direct']", 0),
            ("[class*='stop']", 1),
            ("[data-stops]", 1),
        ]

        for selector, level in selectors:
            try:
                elements = await row.query_selector_all(selector)
                for element in elements[:5]:
                    text = await element.inner_text() or ""
                    aria = await element.get_attribute("aria-label") or ""
                    combined = f"{text} {aria}".lower()

                    if re.search(r'nonstop|non-stop|direct', combined):
                        return ExtractionResult(
                            success=True,
                            value=0,
                            confidence=0.95 - level * 0.05,
                            strategy_name=f"row_{selector}",
                            fallback_level=level,
                            raw_text=combined[:50],
                        )

                    match = re.search(r'(\d+)\s*stop', combined)
                    if match:
                        stops = int(match.group(1))
                        validation = StopsValidator.validate(stops)
                        if validation.is_valid:
                            return ExtractionResult(
                                success=True,
                                value=stops,
                                confidence=validation.confidence - level * 0.05,
                                strategy_name=f"row_{selector}",
                                fallback_level=level,
                                raw_text=combined[:50],
                                validation=validation,
                            )
            except Exception:
                continue

        return None

    @classmethod
    async def _extract_duration(cls, row: ElementHandle) -> Optional[ExtractionResult]:
        """Extract flight duration from within a row element."""
        selectors = [
            ("[aria-label*='duration']", 0),
            ("[aria-label*='hr']", 0),
            ("[aria-label*='hour']", 0),
            ("[class*='duration']", 1),
            ("[class*='total-time']", 1),
        ]

        for selector, level in selectors:
            try:
                elements = await row.query_selector_all(selector)
                for element in elements[:5]:
                    text = await element.inner_text() or ""
                    aria = await element.get_attribute("aria-label") or ""
                    combined = f"{text} {aria}"

                    duration = FlightDetailsExtractor._parse_duration(combined)
                    if duration:
                        validation = DurationValidator.validate(duration)
                        if validation.is_valid:
                            return ExtractionResult(
                                success=True,
                                value=duration,
                                confidence=validation.confidence - level * 0.05,
                                strategy_name=f"row_{selector}",
                                fallback_level=level,
                                raw_text=combined[:50],
                                validation=validation,
                            )
            except Exception:
                continue

        return None


class RowValidator:
    """
    Validates extracted flight rows for consistency and reasonableness.

    Cross-validates fields against each other to catch mismatched data.
    """

    @classmethod
    def validate_row(cls, flight: 'FlightData') -> bool:
        """
        Validate a single flight row. Returns True if the row should be kept.

        A row is invalid if:
        - No price (required field)
        - Price fails validation
        """
        if flight.price is None:
            return False

        validation = PriceValidator.validate(flight.price)
        return validation.is_valid

    @classmethod
    def cross_validate(cls, flight: 'FlightData') -> float:
        """
        Cross-validate fields and return a confidence penalty (0.0 = no penalty).

        Checks for inconsistencies like:
        - Nonstop flight with very long duration (>24h)
        - 2+ stops with very short duration (<2h)
        - Price suspiciously close to duration (scraper confused the two)
        """
        penalty = 0.0

        if flight.stops is not None and flight.duration_minutes is not None:
            # Nonstop but extremely long
            if flight.stops == 0 and flight.duration_minutes > 24 * 60:
                penalty += 0.15
                logger.debug(
                    f"Cross-validation: nonstop flight with {flight.duration_minutes}m "
                    f"duration seems too long, applying penalty"
                )

            # Multiple stops but very short
            if flight.stops >= 2 and flight.duration_minutes < 120:
                penalty += 0.15
                logger.debug(
                    f"Cross-validation: {flight.stops} stops but only "
                    f"{flight.duration_minutes}m seems too short, applying penalty"
                )

        # Price matches duration — almost certainly a misextraction
        if (flight.price is not None and flight.duration_minutes is not None
                and flight.duration_minutes > 0):
            if abs(flight.price - flight.duration_minutes) <= 5:
                penalty += 0.5
                logger.debug(
                    f"Cross-validation: price ${flight.price} matches duration "
                    f"{flight.duration_minutes}m — likely misextracted"
                )

        return penalty


# =============================================================================
# Unified Extraction Interface
# =============================================================================

@dataclass
class FlightData:
    """Extracted flight data with confidence scores."""
    price: Optional[int] = None
    price_confidence: float = 0.0
    price_strategy: str = ""

    airline: Optional[str] = None
    airline_confidence: float = 0.0
    airline_strategy: str = ""

    stops: Optional[int] = None
    stops_confidence: float = 0.0
    stops_strategy: str = ""

    duration_minutes: Optional[int] = None
    duration_confidence: float = 0.0
    duration_strategy: str = ""

    correlation_confidence: float = 0.0  # How sure fields are from same flight
    extraction_method: str = ""  # "per_row" or "page_level"

    overall_confidence: float = 0.0
    extraction_summary: Dict[str, Any] = field(default_factory=dict)

    def calculate_overall_confidence(self) -> float:
        """Calculate overall confidence weighting correlation heavily."""
        field_confidences = [self.price_confidence]
        if self.airline_confidence > 0:
            field_confidences.append(self.airline_confidence)
        if self.stops_confidence > 0:
            field_confidences.append(self.stops_confidence)
        if self.duration_confidence > 0:
            field_confidences.append(self.duration_confidence)

        field_avg = sum(field_confidences) / len(field_confidences)

        if self.correlation_confidence > 0:
            # Weight correlation heavily -- correlated data is far more trustworthy
            self.overall_confidence = field_avg * 0.4 + self.correlation_confidence * 0.6
        else:
            # Legacy path: no correlation data, use field average only
            self.overall_confidence = field_avg

        return self.overall_confidence


class UnifiedExtractor:
    """
    Unified extraction interface that combines all extractors.

    Provides a single entry point for extracting all flight data
    with graceful degradation - extracts what it can, never fails completely.
    """

    @classmethod
    async def extract_all(cls, page: Page) -> List[FlightData]:
        """
        Extract all flight data from page.

        Strategy 1 (primary): Per-row extraction - find flight row containers,
        extract correlated fields from each row. High correlation confidence.

        Strategy 2 (fallback): Page-level extraction - extract flat lists and
        zip by index. Low correlation confidence (the old buggy approach).

        During initial deployment, runs both strategies and logs comparison
        metrics before returning per-row results.
        """
        # Strategy 1: Per-row extraction
        per_row_flights = await cls._extract_per_row(page)

        # Strategy 2: Page-level fallback (always run for comparison logging)
        page_level_flights = await cls._extract_page_level(page)

        # Log comparison between strategies
        if per_row_flights and page_level_flights:
            per_row_prices = sorted(f.price for f in per_row_flights if f.price)
            page_level_prices = sorted(f.price for f in page_level_flights if f.price)
            logger.info(
                f"Extraction comparison - Per-row: {len(per_row_flights)} flights "
                f"(prices: {per_row_prices[:5]}), "
                f"Page-level: {len(page_level_flights)} flights "
                f"(prices: {page_level_prices[:5]})"
            )

        # Use per-row results if available, otherwise fall back to page-level
        if per_row_flights:
            logger.info(
                f"Using per-row extraction: {len(per_row_flights)} flights "
                f"(avg confidence {sum(f.overall_confidence for f in per_row_flights) / len(per_row_flights):.2f})"
            )
            return per_row_flights

        if page_level_flights:
            logger.warning(
                f"Per-row extraction returned no results, falling back to page-level: "
                f"{len(page_level_flights)} flights"
            )
            return page_level_flights

        logger.warning("No flights extracted by any strategy")
        return []

    @classmethod
    async def _extract_per_row(cls, page: Page) -> List[FlightData]:
        """Strategy 1: Per-row extraction with correlated fields."""
        rows, strategy_name, strategy_level = await FlightRowLocator.find_rows(page)

        if not rows:
            return []

        flights = []
        for row in rows:
            try:
                flight = await RowExtractor.extract_from_row(
                    row, strategy_name, strategy_level
                )

                if flight and RowValidator.validate_row(flight):
                    # Apply cross-validation penalty
                    penalty = RowValidator.cross_validate(flight)
                    if penalty > 0:
                        flight.overall_confidence = max(
                            flight.overall_confidence - penalty, 0.1
                        )

                    flights.append(flight)
            except Exception as e:
                logger.debug(f"Row extraction failed: {e}")
                continue

        return flights

    @classmethod
    async def _extract_page_level(cls, page: Page) -> List[FlightData]:
        """
        Strategy 2: Page-level extraction (legacy fallback).

        Extracts flat lists of prices, airlines, stops, durations and zips
        by index. Low correlation confidence since fields may not correspond.
        """
        price_results = await PriceExtractor.extract(page)

        if not price_results:
            return []

        airline_results = await FlightDetailsExtractor.extract_airline(page)
        stops_results = await FlightDetailsExtractor.extract_stops(page)
        duration_results = await FlightDetailsExtractor.extract_duration(page)

        flights = []

        for i, price_result in enumerate(price_results):
            flight = FlightData(
                price=price_result.value,
                price_confidence=price_result.confidence,
                price_strategy=price_result.strategy_name,
            )

            if airline_results:
                airline = airline_results[min(i, len(airline_results) - 1)]
                flight.airline = airline.value
                flight.airline_confidence = airline.confidence
                flight.airline_strategy = airline.strategy_name

            if stops_results:
                stops = stops_results[min(i, len(stops_results) - 1)]
                flight.stops = stops.value
                flight.stops_confidence = stops.confidence
                flight.stops_strategy = stops.strategy_name

            if duration_results:
                duration = duration_results[min(i, len(duration_results) - 1)]
                flight.duration_minutes = duration.value
                flight.duration_confidence = duration.confidence
                flight.duration_strategy = duration.strategy_name

            flight.extraction_method = "page_level"
            flight.correlation_confidence = 0.30 if len(price_results) > 1 else 0.70
            flight.calculate_overall_confidence()

            flight.extraction_summary = {
                "price_strategy": price_result.strategy_name,
                "price_level": price_result.fallback_level,
                "airline_extracted": flight.airline is not None,
                "stops_extracted": flight.stops is not None,
                "duration_extracted": flight.duration_minutes is not None,
                "extraction_method": "page_level",
                "correlation_confidence": flight.correlation_confidence,
            }

            flights.append(flight)

        logger.info(
            f"Page-level extracted {len(flights)} flights. "
            f"Prices: {len(price_results)}, Airlines: {len(airline_results)}, "
            f"Stops: {len(stops_results)}, Durations: {len(duration_results)}"
        )

        return flights
