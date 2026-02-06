"""Tests for RelevanceService and region mapping functions."""
import pytest

from app.models.deal import Deal, DealSource
from app.models.user_settings import UserSettings
from app.services.relevance import (
    RelevanceService,
    get_region_for_airport,
    get_home_region_airports,
    NZ_AIRPORTS,
    AU_AIRPORTS,
    PACIFIC_AIRPORTS,
    MAJOR_HUBS,
)


def _make_deal(origin="AKL", destination="SYD", source=DealSource.SECRET_FLYING):
    return Deal(
        source=source,
        link=f"https://example.com/{origin}-{destination}",
        raw_title=f"Deal: {origin} to {destination}",
        parsed_origin=origin,
        parsed_destination=destination,
        parsed_price=500,
        parsed_currency="NZD",
    )


class TestGetRegionForAirport:
    def test_nz_airports(self):
        assert get_region_for_airport("AKL") == "NZ"
        assert get_region_for_airport("WLG") == "NZ"
        assert get_region_for_airport("CHC") == "NZ"
        assert get_region_for_airport("ZQN") == "NZ"

    def test_au_airports(self):
        assert get_region_for_airport("SYD") == "AU"
        assert get_region_for_airport("MEL") == "AU"
        assert get_region_for_airport("BNE") == "AU"

    def test_pacific_airports(self):
        assert get_region_for_airport("NAN") == "PACIFIC"
        assert get_region_for_airport("HNL") == "PACIFIC"

    def test_unknown_airport(self):
        assert get_region_for_airport("LAX") is None
        assert get_region_for_airport("JFK") is None

    def test_case_insensitive(self):
        assert get_region_for_airport("akl") == "NZ"
        assert get_region_for_airport("Syd") == "AU"


class TestGetHomeRegionAirports:
    def test_nz_home_gets_all_nz(self):
        result = get_home_region_airports({"AKL"})
        assert NZ_AIRPORTS.issubset(result)

    def test_au_home_gets_all_au(self):
        result = get_home_region_airports({"SYD"})
        assert AU_AIRPORTS.issubset(result)

    def test_multiple_regions(self):
        result = get_home_region_airports({"AKL", "SYD"})
        assert NZ_AIRPORTS.issubset(result)
        assert AU_AIRPORTS.issubset(result)

    def test_non_regional_airport(self):
        result = get_home_region_airports({"LAX"})
        assert len(result) == 0

    def test_empty_input(self):
        result = get_home_region_airports(set())
        assert len(result) == 0


class TestRelevanceServiceScoreDeal:
    def test_home_airport_is_relevant(self, db_session):
        UserSettings.get_or_create(db_session)  # AKL default
        svc = RelevanceService(db_session)
        deal = _make_deal(origin="AKL")
        relevant, reason = svc.score_deal(deal)
        assert relevant is True
        assert "AKL" in reason

    def test_home_region_airport_is_relevant(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        # WLG is NZ, same region as AKL
        deal = _make_deal(origin="WLG")
        relevant, reason = svc.score_deal(deal)
        assert relevant is True

    def test_major_hub_is_relevant(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        deal = _make_deal(origin="SIN")
        relevant, reason = svc.score_deal(deal)
        assert relevant is True
        assert "Hub" in reason

    def test_random_origin_not_relevant(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        deal = _make_deal(origin="BOG")  # Bogota -- not a hub or regional
        relevant, reason = svc.score_deal(deal)
        assert relevant is False

    def test_no_origin_not_relevant(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        deal = _make_deal(origin=None)
        deal.parsed_origin = None
        relevant, reason = svc.score_deal(deal)
        assert relevant is False


class TestRelevanceServiceHelpers:
    def test_is_hub_deal(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        assert svc.is_hub_deal(_make_deal(origin="LAX")) is True
        assert svc.is_hub_deal(_make_deal(origin="BOG")) is False

    def test_is_home_deal(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        assert svc.is_home_deal(_make_deal(origin="AKL")) is True
        assert svc.is_home_deal(_make_deal(origin="CHC")) is True  # NZ region
        assert svc.is_home_deal(_make_deal(origin="LAX")) is False

    def test_update_deal_relevance(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        deal = _make_deal(origin="AKL")
        svc.update_deal_relevance(deal)
        assert deal.is_relevant is True
        assert deal.relevance_reason is not None


class TestRelevanceServiceQueries:
    def test_get_relevant_deals(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        d1 = _make_deal(origin="AKL")
        d1.is_relevant = True
        d2 = _make_deal(origin="BOG")
        d2.is_relevant = False
        d2.link = "https://example.com/other"
        db_session.add_all([d1, d2])
        db_session.commit()
        deals = svc.get_relevant_deals()
        assert len(deals) == 1
        assert deals[0].parsed_origin == "AKL"

    def test_get_local_deals(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        d1 = _make_deal(origin="AKL")
        d2 = _make_deal(origin="LAX")
        d2.link = "https://example.com/other"
        db_session.add_all([d1, d2])
        db_session.commit()
        deals = svc.get_local_deals()
        assert len(deals) == 1

    def test_get_hub_deals(self, db_session):
        UserSettings.get_or_create(db_session)
        svc = RelevanceService(db_session)
        d1 = _make_deal(origin="SIN")
        d2 = _make_deal(origin="BOG")
        d2.link = "https://example.com/other"
        db_session.add_all([d1, d2])
        db_session.commit()
        deals = svc.get_hub_deals()
        assert len(deals) == 1
        assert deals[0].parsed_origin == "SIN"
