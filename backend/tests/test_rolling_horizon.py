"""Tests for rolling-horizon date sampling in ScrapingService."""

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.services.scraping_service import ScrapingService


class TestDeterministicSample(unittest.TestCase):
    """Test the deterministic sampling helper."""

    def test_stays_within_bounds(self):
        """Sampled value is always between min and max."""
        for search_id in range(1, 20):
            for day_offset in range(30):
                today = date(2026, 1, 1) + timedelta(days=day_offset)
                val = ScrapingService._deterministic_sample(search_id, today, 30, 90)
                self.assertGreaterEqual(val, 30)
                self.assertLessEqual(val, 90)

    def test_same_day_same_result(self):
        """Same search + same day = same result."""
        today = date(2026, 2, 6)
        a = ScrapingService._deterministic_sample(1, today, 30, 90)
        b = ScrapingService._deterministic_sample(1, today, 30, 90)
        self.assertEqual(a, b)

    def test_different_days_vary(self):
        """Over multiple days, different values are produced."""
        values = set()
        for day_offset in range(30):
            today = date(2026, 1, 1) + timedelta(days=day_offset)
            val = ScrapingService._deterministic_sample(1, today, 30, 90)
            values.add(val)
        # Should produce at least 5 distinct values over 30 days
        self.assertGreaterEqual(len(values), 5)

    def test_different_searches_vary(self):
        """Different search IDs on the same day produce different values."""
        today = date(2026, 2, 6)
        values = set()
        for search_id in range(1, 20):
            val = ScrapingService._deterministic_sample(search_id, today, 30, 90)
            values.add(val)
        # Should produce at least 3 distinct values across 19 searches
        self.assertGreaterEqual(len(values), 3)

    def test_single_value_range(self):
        """When min == max, always returns that value."""
        today = date(2026, 2, 6)
        val = ScrapingService._deterministic_sample(1, today, 60, 60)
        self.assertEqual(val, 60)


class TestGenerateTravelDates(unittest.TestCase):
    """Test _generate_travel_dates with rolling horizon.

    Uses object.__new__ to avoid __init__ side effects (Playwright, DB, etc.)
    """

    def _make_search_def(self, **kwargs):
        mock = MagicMock()
        mock.id = kwargs.get("id", 1)
        mock.departure_date_start = kwargs.get("departure_date_start", None)
        mock.departure_date_end = kwargs.get("departure_date_end", None)
        mock.departure_days_min = kwargs.get("departure_days_min", None)
        mock.departure_days_max = kwargs.get("departure_days_max", None)
        mock.trip_type.value = kwargs.get("trip_type", "round_trip")
        mock.trip_duration_days_min = kwargs.get("trip_duration_days_min", None)
        mock.trip_duration_days_max = kwargs.get("trip_duration_days_max", None)
        return mock

    def _make_service(self):
        """Create a ScrapingService without running __init__."""
        svc = object.__new__(ScrapingService)
        return svc

    def test_fixed_date_uses_start(self):
        """Fixed date mode uses the exact start date."""
        svc = self._make_service()
        start = date(2026, 5, 1)
        end = date(2026, 5, 15)
        search = self._make_search_def(
            departure_date_start=start,
            departure_date_end=end,
            trip_duration_days_min=7,
            trip_duration_days_max=14,
        )
        dep, ret = svc._generate_travel_dates(search)
        self.assertEqual(dep, start)

    def test_rolling_window_stays_in_bounds(self):
        """Rolling window departure date falls within the days range."""
        svc = self._make_service()
        search = self._make_search_def(
            departure_days_min=30,
            departure_days_max=90,
            trip_duration_days_min=7,
            trip_duration_days_max=14,
        )
        today = date.today()
        dep, ret = svc._generate_travel_dates(search)

        days_out = (dep - today).days
        self.assertGreaterEqual(days_out, 30)
        self.assertLessEqual(days_out, 90)

        trip_len = (ret - dep).days
        self.assertGreaterEqual(trip_len, 7)
        self.assertLessEqual(trip_len, 14)

    def test_one_way_has_no_return(self):
        """One-way trips return None for return date."""
        svc = self._make_service()
        search = self._make_search_def(
            departure_days_min=30,
            departure_days_max=90,
            trip_type="one_way",
        )
        dep, ret = svc._generate_travel_dates(search)
        self.assertIsNone(ret)

    def test_fallback_60_days(self):
        """Without any date config, falls back to 60 days from today."""
        svc = self._make_service()
        search = self._make_search_def(
            trip_duration_days_min=7,
            trip_duration_days_max=7,
        )
        dep, ret = svc._generate_travel_dates(search)
        expected = date.today() + timedelta(days=60)
        self.assertEqual(dep, expected)


if __name__ == "__main__":
    unittest.main()
