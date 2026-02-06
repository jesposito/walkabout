"""Tests for the Historical Price Anomaly Guard feature."""
import pytest
from app.services.scraping_service import ScrapingService


class TestIsSuspicious:
    """Tests for ScrapingService._is_suspicious static method."""

    def test_normal_price_not_suspicious(self):
        """A price near the median should not be flagged."""

        class FakeResult:
            price_nzd = 1000

        assert ScrapingService._is_suspicious(FakeResult(), median_price=900, threshold_pct=300) is False

    def test_price_slightly_above_median_not_suspicious(self):
        """A price 50% above median is well within the 300% threshold."""

        class FakeResult:
            price_nzd = 1500

        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000, threshold_pct=300) is False

    def test_spike_flagged_suspicious(self):
        """A price >300% above median should be flagged."""

        class FakeResult:
            price_nzd = 5000

        # 5000 > 1000 * (1 + 300/100) = 4000
        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000, threshold_pct=300) is True

    def test_spike_at_boundary_not_suspicious(self):
        """A price exactly at the boundary should not be flagged (> not >=)."""

        class FakeResult:
            price_nzd = 4000

        # 4000 == 1000 * (1 + 300/100) = 4000 (not strictly greater)
        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000, threshold_pct=300) is False

    def test_crash_flagged_suspicious(self):
        """A price >80% below median (< 20% of median) should be flagged."""

        class FakeResult:
            price_nzd = 100

        # 100 < 1000 * 0.2 = 200
        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000, threshold_pct=300) is True

    def test_crash_at_boundary_not_suspicious(self):
        """A price exactly at 20% of median should not be flagged (< not <=)."""

        class FakeResult:
            price_nzd = 200

        # 200 == 1000 * 0.2 (not strictly less)
        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000, threshold_pct=300) is False

    def test_no_history_not_suspicious(self):
        """With no median (insufficient history), nothing is suspicious."""

        class FakeResult:
            price_nzd = 99999

        assert ScrapingService._is_suspicious(FakeResult(), median_price=None, threshold_pct=300) is False

    def test_custom_threshold_respected(self):
        """A lower threshold should flag more aggressively."""

        class FakeResult:
            price_nzd = 2500

        # With 300% threshold: 2500 < 1000 * 4.0 = 4000 -> not suspicious
        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000, threshold_pct=300) is False

        # With 100% threshold: 2500 > 1000 * 2.0 = 2000 -> suspicious
        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000, threshold_pct=100) is True

    def test_very_cheap_deal_not_flagged(self):
        """A 50% discount is a great deal, not an anomaly."""

        class FakeResult:
            price_nzd = 500

        # 500 > 1000 * 0.2 = 200, so not a crash
        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000, threshold_pct=300) is False

    def test_decimal_price_handling(self):
        """Prices may come as Decimal from the database."""
        from decimal import Decimal

        class FakeResult:
            price_nzd = Decimal("5500.50")

        assert ScrapingService._is_suspicious(FakeResult(), median_price=1000.0, threshold_pct=300) is True


class TestConfidenceColumn:
    """Tests that FlightPrice model has the new columns."""

    def test_flight_price_has_confidence_column(self):
        from app.models.flight_price import FlightPrice
        assert hasattr(FlightPrice, 'confidence')

    def test_flight_price_has_is_suspicious_column(self):
        from app.models.flight_price import FlightPrice
        assert hasattr(FlightPrice, 'is_suspicious')


class TestConfigSetting:
    """Tests that the anomaly threshold config exists."""

    def test_config_has_anomaly_threshold(self):
        from app.config import Settings
        s = Settings(database_url="sqlite:///test.db")
        assert s.price_anomaly_threshold_percent == 300.0

    def test_config_threshold_customizable(self):
        from app.config import Settings
        s = Settings(database_url="sqlite:///test.db", price_anomaly_threshold_percent=150.0)
        assert s.price_anomaly_threshold_percent == 150.0
