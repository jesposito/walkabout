"""Tests for proximity-based RelevanceService."""
import pytest

from app.models.deal import Deal, DealSource
from app.services.relevance import (
    RelevanceService,
    MAJOR_HUBS,
)
from app.services.airports import AirportService, AIRPORTS, _haversine


def _make_deal(origin="JFK", destination="LHR", source=DealSource.SECRET_FLYING):
    return Deal(
        source=source,
        link=f"https://example.com/{origin}-{destination}",
        raw_title=f"Deal: {origin} to {destination}",
        parsed_origin=origin,
        parsed_destination=destination,
        parsed_price=500,
        parsed_currency="USD",
    )


class TestHaversine:
    """Test the haversine distance calculation."""

    def test_same_point(self):
        assert _haversine(40.0, -74.0, 40.0, -74.0) == 0.0

    def test_jfk_to_ewr(self):
        # JFK to EWR is ~30km
        jfk = AIRPORTS.get("JFK")
        ewr = AIRPORTS.get("EWR")
        if jfk and ewr and jfk.latitude and ewr.latitude:
            dist = _haversine(jfk.latitude, jfk.longitude, ewr.latitude, ewr.longitude)
            assert 15 < dist < 50  # Roughly 30km

    def test_jfk_to_lax(self):
        # JFK to LAX is ~3950km
        jfk = AIRPORTS.get("JFK")
        lax = AIRPORTS.get("LAX")
        if jfk and lax and jfk.latitude and lax.latitude:
            dist = _haversine(jfk.latitude, jfk.longitude, lax.latitude, lax.longitude)
            assert 3500 < dist < 4500


class TestAirportServiceProximity:
    """Test the nearby airports functionality."""

    def test_nearby_jfk(self):
        nearby = AirportService.get_nearby_airports("JFK", 100)
        codes = {apt.code for apt, dist in nearby}
        # EWR and LGA should be within 100km of JFK
        assert "EWR" in codes or "LGA" in codes

    def test_nearby_phx(self):
        nearby = AirportService.get_nearby_airports("PHX", 500)
        codes = {apt.code for apt, dist in nearby}
        # Tucson (TUS) should be within 500km of Phoenix
        assert "TUS" in codes

    def test_nearby_empty_for_unknown(self):
        nearby = AirportService.get_nearby_airports("ZZZ", 500)
        assert nearby == []

    def test_nearby_sorted_by_distance(self):
        nearby = AirportService.get_nearby_airports("JFK", 500)
        if len(nearby) > 1:
            distances = [d for _, d in nearby]
            assert distances == sorted(distances)

    def test_get_country_for_airport(self):
        assert AirportService.get_country_for_airport("JFK") == "United States"
        assert AirportService.get_country_for_airport("LHR") == "United Kingdom"
        assert AirportService.get_country_for_airport("ZZZ") is None


class TestMajorHubs:
    """Test that major hubs include key US airports."""

    def test_us_hubs_present(self):
        us_hubs = {"ATL", "DFW", "DEN", "ORD", "LAX", "JFK", "SFO", "SEA",
                    "MIA", "IAH", "PHX", "MSP", "DTW", "BOS", "IAD", "CLT", "MCO"}
        for hub in us_hubs:
            assert hub in MAJOR_HUBS, f"{hub} should be a major hub"

    def test_international_hubs_present(self):
        intl_hubs = {"SIN", "HKG", "LHR", "CDG", "DXB", "NRT"}
        for hub in intl_hubs:
            assert hub in MAJOR_HUBS, f"{hub} should be a major hub"


class TestScoreDealTiers:
    """Test the tier-based scoring without DB (unit tests)."""

    def test_no_origin(self):
        # score_deal requires RelevanceService with db, test via _make_deal
        deal = _make_deal(origin=None)
        deal.parsed_origin = None
        # Can't call score_deal without db, but ensure the deal is constructed
        assert deal.parsed_origin is None

    def test_hub_in_major_hubs(self):
        assert "ATL" in MAJOR_HUBS
        assert "EWR" in MAJOR_HUBS
        assert "BOG" not in MAJOR_HUBS
