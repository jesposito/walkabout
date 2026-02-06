"""Tests for Amadeus enhancements: ISO duration parsing, configurable base URL,
enriched response parsing, carrier resolution, and Price Analysis client."""
import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# parse_iso_duration
# ---------------------------------------------------------------------------
from app.services.flight_price_fetcher import parse_iso_duration


class TestParseIsoDuration:
    def test_hours_and_minutes(self):
        assert parse_iso_duration("PT12H30M") == 750

    def test_hours_only(self):
        assert parse_iso_duration("PT2H") == 120

    def test_minutes_only(self):
        assert parse_iso_duration("PT45M") == 45

    def test_one_hour_zero_minutes(self):
        assert parse_iso_duration("PT1H0M") == 60

    def test_zero_hours_one_minute(self):
        assert parse_iso_duration("PT0H1M") == 1

    def test_none_input(self):
        assert parse_iso_duration(None) is None

    def test_empty_string(self):
        assert parse_iso_duration("") is None

    def test_invalid_format(self):
        assert parse_iso_duration("12H30M") is None

    def test_invalid_with_days(self):
        assert parse_iso_duration("P1DT2H") is None

    def test_just_pt(self):
        # "PT" with no hours or minutes – nothing meaningful
        assert parse_iso_duration("PT") is None

    def test_garbage(self):
        assert parse_iso_duration("garbage") is None


# ---------------------------------------------------------------------------
# Configurable base URL
# ---------------------------------------------------------------------------
from app.services.flight_price_fetcher import AmadeusSource


class TestAmadeusConfigurableBaseUrl:
    @patch("app.services.flight_price_fetcher.settings")
    @patch("app.services.flight_price_fetcher.get_api_key")
    def test_base_url_from_settings(self, mock_get_key, mock_settings):
        mock_settings.amadeus_base_url = "https://test.api.amadeus.com"
        mock_get_key.side_effect = lambda name, db=None: {
            "amadeus_client_id": "cid",
            "amadeus_client_secret": "csec",
        }.get(name)

        source = AmadeusSource.__new__(AmadeusSource)
        source.client_id = "cid"
        source.client_secret = "csec"
        source.base_url = mock_settings.amadeus_base_url.rstrip("/")
        source._token = None
        source._token_expires = None

        assert source.base_url == "https://test.api.amadeus.com"

    @patch("app.services.flight_price_fetcher.settings")
    @patch("app.services.flight_price_fetcher.get_api_key")
    def test_base_url_strips_trailing_slash(self, mock_get_key, mock_settings):
        mock_settings.amadeus_base_url = "https://api.amadeus.com/"
        mock_get_key.side_effect = lambda name, db=None: {
            "amadeus_client_id": "cid",
            "amadeus_client_secret": "csec",
        }.get(name)

        source = AmadeusSource.__new__(AmadeusSource)
        source.client_id = "cid"
        source.client_secret = "csec"
        source.base_url = mock_settings.amadeus_base_url.rstrip("/")
        source._token = None
        source._token_expires = None

        assert source.base_url == "https://api.amadeus.com"

    @patch("app.services.flight_price_fetcher.settings")
    @patch("app.services.flight_price_fetcher.get_api_key")
    def test_token_endpoint_uses_base_url(self, mock_get_key, mock_settings):
        mock_settings.amadeus_base_url = "https://test.api.amadeus.com"
        mock_get_key.side_effect = lambda name, db=None: {
            "amadeus_client_id": "test_id",
            "amadeus_client_secret": "test_secret",
        }.get(name)

        source = AmadeusSource.__new__(AmadeusSource)
        source.client_id = "test_id"
        source.client_secret = "test_secret"
        source.base_url = "https://test.api.amadeus.com"
        source._token = None
        source._token_expires = None

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "tok123",
            "expires_in": 1799,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient", return_value=mock_client):
            token = asyncio.get_event_loop().run_until_complete(source._get_token())

        assert token == "tok123"
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "https://test.api.amadeus.com/v1/security/oauth2/token"


# ---------------------------------------------------------------------------
# Enriched response parsing (duration_minutes + carrier resolution)
# ---------------------------------------------------------------------------

class TestAmadeusResponseParsing:
    def _make_source(self):
        source = AmadeusSource.__new__(AmadeusSource)
        source.client_id = "cid"
        source.client_secret = "csec"
        source.base_url = "https://api.amadeus.com"
        source._token = "valid_token"
        source._token_expires = None
        return source

    def _mock_amadeus_response(self, duration="PT12H30M", carrier_code="NZ",
                                carrier_name="Air New Zealand"):
        return {
            "data": [
                {
                    "price": {"grandTotal": "450.00", "currency": "NZD"},
                    "itineraries": [
                        {
                            "duration": duration,
                            "segments": [
                                {"carrierCode": carrier_code, "departure": {}, "arrival": {}},
                                {"carrierCode": carrier_code, "departure": {}, "arrival": {}},
                            ],
                        }
                    ],
                }
            ],
            "dictionaries": {
                "carriers": {carrier_code: carrier_name},
            },
        }

    def test_duration_minutes_extracted(self):
        source = self._make_source()
        source._get_token = AsyncMock(return_value="valid_token")

        resp_data = self._mock_amadeus_response(duration="PT12H30M")
        mock_response = MagicMock()
        mock_response.json.return_value = resp_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL", destination="SYD",
                    departure_date=date(2026, 3, 15),
                    return_date=None, adults=2, children=0,
                    cabin_class="economy", currency="NZD",
                )
            )

        assert result.success
        assert len(result.prices) == 1
        assert result.prices[0].duration_minutes == 750

    def test_carrier_resolved_from_dictionaries(self):
        source = self._make_source()
        source._get_token = AsyncMock(return_value="valid_token")

        resp_data = self._mock_amadeus_response(
            carrier_code="QF", carrier_name="Qantas"
        )
        mock_response = MagicMock()
        mock_response.json.return_value = resp_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL", destination="SYD",
                    departure_date=date(2026, 3, 15),
                    return_date=None, adults=2, children=0,
                    cabin_class="economy", currency="NZD",
                )
            )

        assert result.success
        assert result.prices[0].airline == "Qantas"

    def test_carrier_fallback_to_code_when_not_in_dict(self):
        source = self._make_source()
        source._get_token = AsyncMock(return_value="valid_token")

        resp_data = self._mock_amadeus_response(
            carrier_code="XX", carrier_name="Some Airline"
        )
        # Remove the carrier from dictionaries to test fallback
        resp_data["dictionaries"]["carriers"] = {}
        mock_response = MagicMock()
        mock_response.json.return_value = resp_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL", destination="SYD",
                    departure_date=date(2026, 3, 15),
                    return_date=None, adults=2, children=0,
                    cabin_class="economy", currency="NZD",
                )
            )

        assert result.success
        # Falls back to carrier code when not in dictionaries
        assert result.prices[0].airline == "XX"

    def test_nonstop_explicit_false(self):
        """When stops_filter is not 'nonstop', nonStop should be set to 'false'."""
        source = self._make_source()
        source._get_token = AsyncMock(return_value="valid_token")

        resp_data = self._mock_amadeus_response()
        mock_response = MagicMock()
        mock_response.json.return_value = resp_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient", return_value=mock_client):
            asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL", destination="SYD",
                    departure_date=date(2026, 3, 15),
                    return_date=None, adults=2, children=0,
                    cabin_class="economy", currency="NZD",
                    stops_filter="any",
                )
            )

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["nonStop"] == "false"

    def test_nonstop_explicit_true(self):
        """When stops_filter is 'nonstop', nonStop should be 'true'."""
        source = self._make_source()
        source._get_token = AsyncMock(return_value="valid_token")

        resp_data = self._mock_amadeus_response()
        mock_response = MagicMock()
        mock_response.json.return_value = resp_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient", return_value=mock_client):
            asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL", destination="SYD",
                    departure_date=date(2026, 3, 15),
                    return_date=None, adults=2, children=0,
                    cabin_class="economy", currency="NZD",
                    stops_filter="nonstop",
                )
            )

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["nonStop"] == "true"

    def test_no_duration_in_response(self):
        """When itinerary has no duration field, duration_minutes should be None."""
        source = self._make_source()
        source._get_token = AsyncMock(return_value="valid_token")

        resp_data = self._mock_amadeus_response()
        # Remove duration from the itinerary
        resp_data["data"][0]["itineraries"][0].pop("duration", None)
        mock_response = MagicMock()
        mock_response.json.return_value = resp_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.flight_price_fetcher.httpx.AsyncClient", return_value=mock_client):
            result = asyncio.get_event_loop().run_until_complete(
                source.fetch_prices(
                    origin="AKL", destination="SYD",
                    departure_date=date(2026, 3, 15),
                    return_date=None, adults=2, children=0,
                    cabin_class="economy", currency="NZD",
                )
            )

        assert result.success
        assert result.prices[0].duration_minutes is None


# ---------------------------------------------------------------------------
# Price Analysis client
# ---------------------------------------------------------------------------
from app.services.amadeus_price_analysis import (
    AmadeusPriceAnalysis,
    PriceAnalysisResult,
    PriceMetric,
)


class TestPriceAnalysisClient:
    SAMPLE_RESPONSE = {
        "data": [
            {
                "type": "itinerary-price-metric",
                "origin": {"iataCode": "AKL"},
                "destination": {"iataCode": "SYD"},
                "departureDate": "2026-03-15",
                "priceMetrics": [
                    {"quartileRanking": "MINIMUM", "amount": "150.00"},
                    {"quartileRanking": "FIRST", "amount": "200.00"},
                    {"quartileRanking": "MEDIUM", "amount": "280.00"},
                    {"quartileRanking": "THIRD", "amount": "350.00"},
                    {"quartileRanking": "MAXIMUM", "amount": "600.00"},
                ],
            }
        ]
    }

    def _make_client(self):
        client = AmadeusPriceAnalysis.__new__(AmadeusPriceAnalysis)
        client.client_id = "cid"
        client.client_secret = "csec"
        client.base_url = "https://test.api.amadeus.com"
        client._token = "valid_token"
        client._token_expires = None
        return client

    def test_parse_price_metrics(self):
        client = self._make_client()
        client._get_token = AsyncMock(return_value="valid_token")

        mock_response = MagicMock()
        mock_response.json.return_value = self.SAMPLE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.amadeus_price_analysis.httpx.AsyncClient", return_value=mock_http):
            result = asyncio.get_event_loop().run_until_complete(
                client.get_price_metrics(
                    origin="AKL",
                    destination="SYD",
                    departure_date=date(2026, 3, 15),
                    currency_code="NZD",
                )
            )

        assert result.success
        assert result.origin == "AKL"
        assert result.destination == "SYD"
        assert result.departure_date == "2026-03-15"
        assert len(result.metrics) == 5
        assert result.minimum == Decimal("150.00")
        assert result.first_quartile == Decimal("200.00")
        assert result.median == Decimal("280.00")
        assert result.third_quartile == Decimal("350.00")
        assert result.maximum == Decimal("600.00")

    def test_price_metrics_uses_correct_endpoint(self):
        client = self._make_client()
        client._get_token = AsyncMock(return_value="valid_token")

        mock_response = MagicMock()
        mock_response.json.return_value = self.SAMPLE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.amadeus_price_analysis.httpx.AsyncClient", return_value=mock_http):
            asyncio.get_event_loop().run_until_complete(
                client.get_price_metrics(
                    origin="AKL",
                    destination="SYD",
                    departure_date=date(2026, 3, 15),
                )
            )

        call_args = mock_http.get.call_args
        assert call_args[0][0] == "https://test.api.amadeus.com/v1/analytics/itinerary-price-metrics"

    def test_price_metrics_passes_params(self):
        client = self._make_client()
        client._get_token = AsyncMock(return_value="valid_token")

        mock_response = MagicMock()
        mock_response.json.return_value = self.SAMPLE_RESPONSE
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.amadeus_price_analysis.httpx.AsyncClient", return_value=mock_http):
            asyncio.get_event_loop().run_until_complete(
                client.get_price_metrics(
                    origin="AKL",
                    destination="SYD",
                    departure_date=date(2026, 3, 15),
                    currency_code="NZD",
                    one_way=False,
                )
            )

        call_args = mock_http.get.call_args
        params = call_args[1]["params"]
        assert params["originIataCode"] == "AKL"
        assert params["destinationIataCode"] == "SYD"
        assert params["departureDate"] == "2026-03-15"
        assert params["currencyCode"] == "NZD"
        assert params["oneWay"] == "false"

    def test_not_available_returns_error(self):
        client = self._make_client()
        client.client_id = ""
        client.client_secret = ""

        result = asyncio.get_event_loop().run_until_complete(
            client.get_price_metrics(
                origin="AKL",
                destination="SYD",
                departure_date=date(2026, 3, 15),
            )
        )

        assert not result.success
        assert "not configured" in result.error

    def test_auth_failure_returns_error(self):
        client = self._make_client()
        client._get_token = AsyncMock(return_value=None)

        result = asyncio.get_event_loop().run_until_complete(
            client.get_price_metrics(
                origin="AKL",
                destination="SYD",
                departure_date=date(2026, 3, 15),
            )
        )

        assert not result.success
        assert "authenticate" in result.error

    def test_empty_data_returns_error(self):
        client = self._make_client()
        client._get_token = AsyncMock(return_value="valid_token")

        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        with patch("app.services.amadeus_price_analysis.httpx.AsyncClient", return_value=mock_http):
            result = asyncio.get_event_loop().run_until_complete(
                client.get_price_metrics(
                    origin="AKL",
                    destination="SYD",
                    departure_date=date(2026, 3, 15),
                )
            )

        assert not result.success
        assert "No price metric data" in result.error

    def test_quartile_property_returns_none_when_missing(self):
        result = PriceAnalysisResult(success=True, metrics=[])
        assert result.minimum is None
        assert result.first_quartile is None
        assert result.median is None
        assert result.third_quartile is None
        assert result.maximum is None
