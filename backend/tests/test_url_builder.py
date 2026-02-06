"""
Tests for the centralized Google Flights URL builder and filter passthrough.
"""
import pytest
from datetime import date
from urllib.parse import unquote

from app.utils.template_helpers import build_google_flights_url


class TestBuildGoogleFlightsUrl:
    """Tests for build_google_flights_url()."""

    def test_basic_one_way(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
        )
        decoded = unquote(url)
        assert "google.com/travel/flights" in url
        assert "AKL" in decoded
        assert "LAX" in decoded
        assert "2026-06-15" in decoded
        assert "curr=NZD" in url

    def test_round_trip_includes_return_date(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="NRT",
            departure_date=date(2026, 7, 1),
            return_date=date(2026, 7, 15),
        )
        decoded = unquote(url)
        assert "returning 2026-07-15" in decoded

    def test_no_return_date_omits_returning(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="SIN",
            departure_date=date(2026, 8, 1),
        )
        decoded = unquote(url)
        assert "returning" not in decoded

    def test_business_class_hint(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LHR",
            departure_date=date(2026, 6, 15),
            cabin_class="business",
        )
        decoded = unquote(url)
        assert "business class" in decoded

    def test_first_class_hint(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LHR",
            departure_date=date(2026, 6, 15),
            cabin_class="first",
        )
        decoded = unquote(url)
        assert "first class" in decoded

    def test_premium_economy_hint(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LHR",
            departure_date=date(2026, 6, 15),
            cabin_class="premium_economy",
        )
        decoded = unquote(url)
        assert "premium economy" in decoded

    def test_economy_no_class_hint(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LHR",
            departure_date=date(2026, 6, 15),
            cabin_class="economy",
        )
        decoded = unquote(url)
        assert "business class" not in decoded
        assert "first class" not in decoded

    def test_nonstop_filter(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="SYD",
            departure_date=date(2026, 6, 15),
            stops_filter="nonstop",
        )
        decoded = unquote(url)
        assert "nonstop" in decoded

    def test_one_stop_filter(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            stops_filter="one_stop",
        )
        decoded = unquote(url)
        assert "1 stop or fewer" in decoded

    def test_any_stops_no_hint(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            stops_filter="any",
        )
        decoded = unquote(url)
        assert "nonstop" not in decoded
        assert "stop" not in decoded

    def test_multiple_adults(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            adults=3,
        )
        decoded = unquote(url)
        assert "3 adults" in decoded

    def test_children_passengers(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            adults=2,
            children=2,
        )
        decoded = unquote(url)
        assert "2 adults" in decoded
        assert "2 children" in decoded

    def test_single_child(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            adults=2,
            children=1,
        )
        decoded = unquote(url)
        assert "1 child" in decoded
        assert "children" not in decoded

    def test_infants(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            adults=2,
            infants_in_seat=1,
        )
        decoded = unquote(url)
        assert "1 infant" in decoded

    def test_multiple_infants(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            adults=2,
            infants_in_seat=1,
            infants_on_lap=1,
        )
        decoded = unquote(url)
        assert "2 infants" in decoded

    def test_single_adult_no_passenger_hint(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            adults=1,
        )
        decoded = unquote(url)
        assert "adults" not in decoded

    def test_currency_parameter(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
            currency="USD",
        )
        assert "curr=USD" in url

    def test_locale_parameters(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="LAX",
            departure_date=date(2026, 6, 15),
        )
        assert "hl=en" in url
        assert "gl=nz" in url

    def test_all_filters_combined(self):
        url = build_google_flights_url(
            origin="AKL",
            destination="NRT",
            departure_date=date(2026, 9, 1),
            return_date=date(2026, 9, 14),
            adults=2,
            children=1,
            infants_on_lap=1,
            cabin_class="business",
            stops_filter="nonstop",
            currency="NZD",
        )
        decoded = unquote(url)
        assert "AKL" in decoded
        assert "NRT" in decoded
        assert "2026-09-01" in decoded
        assert "returning 2026-09-14" in decoded
        assert "business class" in decoded
        assert "nonstop" in decoded
        assert "2 adults" in decoded
        assert "1 child" in decoded
        assert "1 infant" in decoded
        assert "curr=NZD" in url
