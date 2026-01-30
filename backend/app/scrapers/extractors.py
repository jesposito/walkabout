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
        (r'\b(\d{3,5})\b', "Bare number"),
    ]

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

    overall_confidence: float = 0.0
    extraction_summary: Dict[str, Any] = field(default_factory=dict)


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

        Returns list of FlightData objects, one per detected flight.
        Gracefully degrades - returns partial data if full extraction fails.
        """
        # Extract prices first (required)
        price_results = await PriceExtractor.extract(page)

        if not price_results:
            logger.warning("No prices extracted - returning empty results")
            return []

        # Extract supplementary data
        airline_results = await FlightDetailsExtractor.extract_airline(page)
        stops_results = await FlightDetailsExtractor.extract_stops(page)
        duration_results = await FlightDetailsExtractor.extract_duration(page)

        # Build flight data objects
        flights = []

        for i, price_result in enumerate(price_results):
            flight = FlightData(
                price=price_result.value,
                price_confidence=price_result.confidence,
                price_strategy=price_result.strategy_name,
            )

            # Try to match with airline (use index if available, else best match)
            if airline_results:
                airline = airline_results[min(i, len(airline_results) - 1)]
                flight.airline = airline.value
                flight.airline_confidence = airline.confidence
                flight.airline_strategy = airline.strategy_name

            # Try to match with stops
            if stops_results:
                stops = stops_results[min(i, len(stops_results) - 1)]
                flight.stops = stops.value
                flight.stops_confidence = stops.confidence
                flight.stops_strategy = stops.strategy_name

            # Try to match with duration
            if duration_results:
                duration = duration_results[min(i, len(duration_results) - 1)]
                flight.duration_minutes = duration.value
                flight.duration_confidence = duration.confidence
                flight.duration_strategy = duration.strategy_name

            # Calculate overall confidence
            confidences = [flight.price_confidence]
            if flight.airline_confidence > 0:
                confidences.append(flight.airline_confidence)
            if flight.stops_confidence > 0:
                confidences.append(flight.stops_confidence)
            if flight.duration_confidence > 0:
                confidences.append(flight.duration_confidence)

            flight.overall_confidence = sum(confidences) / len(confidences)

            # Build extraction summary
            flight.extraction_summary = {
                "price_strategy": price_result.strategy_name,
                "price_level": price_result.fallback_level,
                "airline_extracted": flight.airline is not None,
                "stops_extracted": flight.stops is not None,
                "duration_extracted": flight.duration_minutes is not None,
            }

            flights.append(flight)

        # Log summary
        logger.info(
            f"Extracted {len(flights)} flights. "
            f"Prices: {len(price_results)}, Airlines: {len(airline_results)}, "
            f"Stops: {len(stops_results)}, Durations: {len(duration_results)}"
        )

        return flights
