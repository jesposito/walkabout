"""Tests for SerpAPI enhancements: deep_search, price_insights, gl parameter, and deal rating integration."""
import asyncio
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.flight_price_fetcher import (
    SerpAPISource,
    FetchResult,
    PriceResult,
    determine_gl,
    NZ_AIRPORTS,
    AU_AIRPORTS,
)
from app.services.deal_rating import calculate_rating, RATING_LABELS


# --- gl parameter tests ---

class TestDetermineGl:
    def test_nz_airports(self):
        for code in NZ_AIRPORTS:
            assert determine_gl(code) == "nz", f"Expected 'nz' for {code}"

    def test_au_airports(self):
        for code in AU_AIRPORTS:
            assert determine_gl(code) == "au", f"Expected 'au' for {code}"

    def test_nz_lowercase(self):
        assert determine_gl("akl") == "nz"

    def test_au_lowercase(self):
        assert determine_gl("syd") == "au"

    def test_other_airport_returns_none(self):
        assert determine_gl("LAX") is None
        assert determine_gl("LHR") is None
        assert determine_gl("NRT") is None

    def test_empty_string_returns_none(self):
        assert determine_gl("") is None


# --- SerpAPI fetch_prices tests ---

def _make_serpapi_response(price_insights=None, flights=None):
    """Build a mock SerpAPI JSON response."""
    data = {}
    if flights is not None:
        data["best_flights"] = flights
    else:
        data["best_flights"] = [
            {
                "price": 350,
                "total_duration": 195,
                "flights": [
                    {
                        "airline": "Air New Zealand",
                        "departure_airport": {"time": "06:00"},
                        "arrival_airport": {"time": "09:15"},
                    }
                ],
            }
        ]
    data["other_flights"] = []
    if price_insights is not None:
        data["price_insights"] = price_insights
    return data


class TestSerpAPIDeepSearch:
    """Verify deep_search=True is included in request params."""

    def test_deep_search_in_params(self):
        """deep_search=True should appear in the params dict sent to SerpAPI."""
        captured_params = {}

        async def fake_get(url, params=None, **kwargs):
            captured_params.update(params or {})
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=_make_serpapi_response())
            return resp

        source = SerpAPISource.__new__(SerpAPISource)
        source.api_key = "test-key"

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL",
                    destination="SYD",
                    departure_date=date(2026, 6, 15),
                    return_date=date(2026, 6, 22),
                    adults=2,
                    children=0,
                    cabin_class="economy",
                    currency="NZD",
                )
            )

        assert captured_params.get("deep_search") is True
        assert result.success is True


class TestSerpAPIGlParam:
    """Verify gl parameter is set based on origin airport."""

    def _run_fetch(self, origin):
        captured_params = {}

        async def fake_get(url, params=None, **kwargs):
            captured_params.update(params or {})
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=_make_serpapi_response())
            return resp

        source = SerpAPISource.__new__(SerpAPISource)
        source.api_key = "test-key"

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin=origin,
                    destination="LAX",
                    departure_date=date(2026, 6, 15),
                    return_date=None,
                    adults=1,
                    children=0,
                    cabin_class="economy",
                    currency="NZD",
                )
            )

        return captured_params

    def test_nz_origin_sets_gl(self):
        params = self._run_fetch("AKL")
        assert params.get("gl") == "nz"

    def test_au_origin_sets_gl(self):
        params = self._run_fetch("SYD")
        assert params.get("gl") == "au"

    def test_other_origin_no_gl(self):
        params = self._run_fetch("LAX")
        assert "gl" not in params


class TestSerpAPIPriceInsights:
    """Verify price_insights is extracted from SerpAPI response."""

    def test_price_insights_extracted(self):
        insights = {
            "lowest_price": 234,
            "price_level": "low",
            "typical_price_range": [250, 400],
            "price_history": [[1700000000000, 350], [1700100000000, 345]],
        }

        async def fake_get(url, params=None, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=_make_serpapi_response(price_insights=insights))
            return resp

        source = SerpAPISource.__new__(SerpAPISource)
        source.api_key = "test-key"

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL",
                    destination="SYD",
                    departure_date=date(2026, 6, 15),
                    return_date=date(2026, 6, 22),
                    adults=2,
                    children=0,
                    cabin_class="economy",
                    currency="NZD",
                )
            )

        assert result.success is True
        assert result.price_insights is not None
        assert result.price_insights["lowest_price"] == 234
        assert result.price_insights["price_level"] == "low"
        assert result.price_insights["typical_price_range"] == [250, 400]

    def test_no_price_insights_returns_none(self):
        """When SerpAPI response has no price_insights field, result should have None."""

        async def fake_get(url, params=None, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json = MagicMock(return_value=_make_serpapi_response(price_insights=None))
            return resp

        source = SerpAPISource.__new__(SerpAPISource)
        source.api_key = "test-key"

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = fake_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL",
                    destination="SYD",
                    departure_date=date(2026, 6, 15),
                    return_date=date(2026, 6, 22),
                    adults=2,
                    children=0,
                    cabin_class="economy",
                    currency="NZD",
                )
            )

        assert result.success is True
        assert result.price_insights is None


# --- FetchResult dataclass tests ---

class TestFetchResultPriceInsights:
    def test_default_price_insights_is_none(self):
        result = FetchResult(success=True, source="test")
        assert result.price_insights is None

    def test_price_insights_can_be_set(self):
        insights = {"price_level": "low", "lowest_price": 100}
        result = FetchResult(success=True, source="test", price_insights=insights)
        assert result.price_insights == insights


# --- Deal rating with price_level tests ---

class TestDealRatingWithPriceLevel:
    def test_price_level_low_promotes_to_decent(self):
        """A small savings with price_level='low' should still be rated as decent."""
        # 3% savings would normally be "Normal", but price_level="low" promotes it
        savings, label = calculate_rating(970, 1000, price_level="low")
        assert savings == pytest.approx(3.0)
        assert label == RATING_LABELS["decent"]

    def test_price_level_low_keeps_hot_deal(self):
        """price_level='low' should not downgrade a hot deal."""
        savings, label = calculate_rating(600, 1000, price_level="low")
        assert savings == 40.0
        assert label == RATING_LABELS["hot"]

    def test_price_level_low_keeps_good_deal(self):
        """price_level='low' should not downgrade a good deal."""
        savings, label = calculate_rating(800, 1000, price_level="low")
        assert savings == 20.0
        assert label == RATING_LABELS["good"]

    def test_price_level_high_caps_at_normal(self):
        """price_level='high' with positive savings should cap at normal."""
        savings, label = calculate_rating(900, 1000, price_level="high")
        assert savings == 10.0
        assert label == RATING_LABELS["normal"]

    def test_price_level_high_above_market(self):
        """price_level='high' with negative savings should be 'above market'."""
        savings, label = calculate_rating(1100, 1000, price_level="high")
        assert savings == -10.0
        assert label == RATING_LABELS["above"]

    def test_price_level_typical_no_change(self):
        """price_level='typical' should not alter the normal rating logic."""
        savings, label = calculate_rating(800, 1000, price_level="typical")
        assert savings == 20.0
        assert label == RATING_LABELS["good"]

    def test_price_level_none_no_change(self):
        """price_level=None should not alter the normal rating logic."""
        savings, label = calculate_rating(800, 1000, price_level=None)
        assert savings == 20.0
        assert label == RATING_LABELS["good"]

    def test_suspicious_overrides_price_level(self):
        """Suspicious savings threshold should still override price_level='low'."""
        # 85% savings with price_level="low" should still be flagged as suspicious
        savings, label = calculate_rating(150, 1000, price_level="low")
        assert savings == 85.0
        assert label == RATING_LABELS["suspicious"]
