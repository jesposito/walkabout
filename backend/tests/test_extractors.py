"""
Tests for the flight data extraction pipeline.

Tests FlightData confidence calculation, RowValidator, PriceValidator,
bare number regex removal, and confidence gate thresholds.
"""
import pytest
from decimal import Decimal

from app.scrapers.extractors import (
    FlightData,
    PriceValidator,
    RowValidator,
    PriceExtractor,
)


class TestFlightDataConfidence:
    """Tests for FlightData.calculate_overall_confidence()."""

    def test_price_only_no_correlation(self):
        """Price-only extraction with no correlation uses field average."""
        flight = FlightData(price=500, price_confidence=0.9)
        result = flight.calculate_overall_confidence()
        assert result == 0.9

    def test_price_with_high_correlation(self):
        """Per-row extraction with high correlation should boost confidence."""
        flight = FlightData(
            price=500,
            price_confidence=0.8,
            correlation_confidence=0.95,
        )
        result = flight.calculate_overall_confidence()
        # 0.8 * 0.4 + 0.95 * 0.6 = 0.32 + 0.57 = 0.89
        assert abs(result - 0.89) < 0.01

    def test_multiple_fields_with_correlation(self):
        """All fields present: average of field confidences weighted with correlation."""
        flight = FlightData(
            price=500,
            price_confidence=0.9,
            airline="Air NZ",
            airline_confidence=0.8,
            stops=1,
            stops_confidence=0.7,
            duration_minutes=600,
            duration_confidence=0.6,
            correlation_confidence=0.95,
        )
        result = flight.calculate_overall_confidence()
        # field_avg = (0.9 + 0.8 + 0.7 + 0.6) / 4 = 0.75
        # overall = 0.75 * 0.4 + 0.95 * 0.6 = 0.30 + 0.57 = 0.87
        assert abs(result - 0.87) < 0.01

    def test_zero_confidence_fields_excluded(self):
        """Fields with 0 confidence should not be included in average."""
        flight = FlightData(
            price=500,
            price_confidence=0.9,
            airline_confidence=0.0,  # Should be excluded
            stops_confidence=0.0,   # Should be excluded
        )
        result = flight.calculate_overall_confidence()
        # Only price_confidence counted
        assert result == 0.9

    def test_page_level_low_correlation(self):
        """Page-level fallback extraction should have low overall confidence."""
        flight = FlightData(
            price=500,
            price_confidence=0.8,
            correlation_confidence=0.30,  # Page-level
        )
        result = flight.calculate_overall_confidence()
        # 0.8 * 0.4 + 0.30 * 0.6 = 0.32 + 0.18 = 0.50
        assert abs(result - 0.50) < 0.01


class TestRowValidatorCorrelation:
    """Tests for RowExtractor._correlation_for_level()."""

    def test_level_0_highest(self):
        """Level 0 (Google-specific selectors) = 0.95."""
        from app.scrapers.extractors import RowExtractor
        assert RowExtractor._correlation_for_level(0) == 0.95

    def test_level_1_high(self):
        """Level 1 (category-scoped) = 0.90."""
        from app.scrapers.extractors import RowExtractor
        assert RowExtractor._correlation_for_level(1) == 0.90

    def test_level_2_high(self):
        """Level 2 (ARIA-based) = 0.90."""
        from app.scrapers.extractors import RowExtractor
        assert RowExtractor._correlation_for_level(2) == 0.90

    def test_level_3_moderate(self):
        """Level 3 (DOM traversal) = 0.80."""
        from app.scrapers.extractors import RowExtractor
        assert RowExtractor._correlation_for_level(3) == 0.80

    def test_unknown_level_fallback(self):
        """Unknown levels default to 0.70."""
        from app.scrapers.extractors import RowExtractor
        assert RowExtractor._correlation_for_level(99) == 0.70


class TestRowValidator:
    """Tests for RowValidator."""

    def test_valid_row_with_price(self):
        flight = FlightData(price=500, price_confidence=0.9)
        assert RowValidator.validate_row(flight) is True

    def test_invalid_row_no_price(self):
        flight = FlightData(price=None)
        assert RowValidator.validate_row(flight) is False

    def test_invalid_row_price_too_low(self):
        flight = FlightData(price=10, price_confidence=0.9)
        assert RowValidator.validate_row(flight) is False

    def test_invalid_row_price_too_high(self):
        flight = FlightData(price=100000, price_confidence=0.9)
        assert RowValidator.validate_row(flight) is False

    def test_cross_validate_no_penalty_normal(self):
        flight = FlightData(price=500, stops=1, duration_minutes=600)
        penalty = RowValidator.cross_validate(flight)
        assert penalty == 0.0

    def test_cross_validate_nonstop_too_long(self):
        flight = FlightData(price=500, stops=0, duration_minutes=25 * 60)
        penalty = RowValidator.cross_validate(flight)
        assert penalty > 0  # Should penalize nonstop with 25h duration

    def test_cross_validate_many_stops_too_short(self):
        flight = FlightData(price=500, stops=3, duration_minutes=90)
        penalty = RowValidator.cross_validate(flight)
        assert penalty > 0  # Should penalize 3 stops with 90min duration

    def test_cross_validate_missing_fields_no_penalty(self):
        flight = FlightData(price=500)
        penalty = RowValidator.cross_validate(flight)
        assert penalty == 0.0


class TestPriceValidator:
    """Tests for PriceValidator."""

    def test_valid_price(self):
        result = PriceValidator.validate(800)
        assert result.is_valid is True
        assert result.confidence > 0.5

    def test_price_below_minimum(self):
        result = PriceValidator.validate(10)
        assert result.is_valid is False

    def test_price_above_maximum(self):
        result = PriceValidator.validate(100000)
        assert result.is_valid is False

    def test_suspicious_price_rejected(self):
        result = PriceValidator.validate(1000)
        # 1000 is in SUSPICIOUS_PRICES -- rejected as likely UI element
        assert result.is_valid is False
        assert result.confidence < 0.5


class TestBareNumberRegexRemoval:
    """Tests verifying bare number regex is no longer in PRICE_PATTERNS."""

    def test_no_bare_number_pattern(self):
        """Bare number regex should NOT be in the main PRICE_PATTERNS."""
        import re
        bare_number = re.compile(r'\b(\d{3,5})\b')

        # Check that PRICE_PATTERNS doesn't contain the bare number regex
        for pattern in PriceExtractor.PRICE_PATTERNS:
            # Pattern could be tuple (pattern, confidence) or just pattern
            if isinstance(pattern, tuple):
                pat = pattern[0]
            else:
                pat = pattern

            pat_str = str(pat) if not isinstance(pat, str) else pat
            # The bare number regex matches things like "747" (flight number)
            # It should not be in main patterns
            assert pat_str != r'\b(\d{3,5})\b', \
                "Bare number regex should be removed from PRICE_PATTERNS"


class TestConfidenceGateThresholds:
    """Tests for the confidence gating thresholds in scraping_service.py."""

    def test_storage_threshold(self):
        """MIN_CONFIDENCE_FOR_STORAGE should be 0.5."""
        from app.services.scraping_service import ScrapingService
        assert ScrapingService.MIN_CONFIDENCE_FOR_STORAGE == 0.5

    def test_deals_threshold(self):
        """MIN_CONFIDENCE_FOR_DEALS should be 0.6."""
        from app.services.scraping_service import ScrapingService
        assert ScrapingService.MIN_CONFIDENCE_FOR_DEALS == 0.6

    def test_deals_threshold_higher_than_storage(self):
        """Deal analysis threshold must be higher than storage threshold."""
        from app.services.scraping_service import ScrapingService
        assert ScrapingService.MIN_CONFIDENCE_FOR_DEALS > ScrapingService.MIN_CONFIDENCE_FOR_STORAGE


class TestConfidenceGateClassification:
    """Tests that confidence values correctly classify into store/reject/deal-eligible."""

    def test_below_storage_rejected(self):
        """Flights with confidence < 0.5 should be rejected."""
        from app.services.scraping_service import ScrapingService
        confidence = 0.45
        assert confidence < ScrapingService.MIN_CONFIDENCE_FOR_STORAGE

    def test_between_storage_and_deals(self):
        """Flights with 0.5 <= confidence < 0.6 should be stored but not analyzed for deals."""
        from app.services.scraping_service import ScrapingService
        confidence = 0.55
        assert confidence >= ScrapingService.MIN_CONFIDENCE_FOR_STORAGE
        assert confidence < ScrapingService.MIN_CONFIDENCE_FOR_DEALS

    def test_above_deals_threshold(self):
        """Flights with confidence >= 0.6 should be stored and analyzed for deals."""
        from app.services.scraping_service import ScrapingService
        confidence = 0.75
        assert confidence >= ScrapingService.MIN_CONFIDENCE_FOR_STORAGE
        assert confidence >= ScrapingService.MIN_CONFIDENCE_FOR_DEALS

    def test_page_level_low_correlation_below_storage(self):
        """Page-level extraction with low field confidence should be rejected."""
        flight = FlightData(
            price=500,
            price_confidence=0.6,
            correlation_confidence=0.30,
        )
        overall = flight.calculate_overall_confidence()
        # 0.6 * 0.4 + 0.3 * 0.6 = 0.24 + 0.18 = 0.42
        from app.services.scraping_service import ScrapingService
        assert overall < ScrapingService.MIN_CONFIDENCE_FOR_STORAGE

    def test_per_row_high_confidence_above_deals(self):
        """Per-row extraction with good field confidence should be deal-eligible."""
        flight = FlightData(
            price=500,
            price_confidence=0.85,
            airline="Air NZ",
            airline_confidence=0.9,
            correlation_confidence=0.95,
        )
        overall = flight.calculate_overall_confidence()
        # field_avg = (0.85 + 0.9) / 2 = 0.875
        # overall = 0.875 * 0.4 + 0.95 * 0.6 = 0.35 + 0.57 = 0.92
        from app.services.scraping_service import ScrapingService
        assert overall >= ScrapingService.MIN_CONFIDENCE_FOR_DEALS
