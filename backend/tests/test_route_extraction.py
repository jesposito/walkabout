"""Tests for AirportLookup.extract_route() — ensuring routes are only extracted
when there's structural evidence (separators, to/from patterns), not from
incidental city mentions."""

import pytest
from app.services.airports import AirportLookup


class TestExplicitRoutePatterns:
    """Routes with clear structural indicators should be extracted."""

    def test_em_dash_separator(self):
        origin, dest = AirportLookup.extract_route("Auckland – London from $599")
        assert origin == "AKL"
        assert dest == "LHR"

    def test_en_dash_separator(self):
        origin, dest = AirportLookup.extract_route("Sydney — Tokyo for $899")
        assert origin == "SYD"
        assert dest == "NRT"

    def test_arrow_separator(self):
        origin, dest = AirportLookup.extract_route("AKL → SYD $299 return")
        assert origin == "AKL"
        assert dest == "SYD"

    def test_to_keyword(self):
        origin, dest = AirportLookup.extract_route("Auckland to Sydney from $299")
        assert origin == "AKL"
        assert dest == "SYD"

    def test_to_keyword_with_codes(self):
        origin, dest = AirportLookup.extract_route("AKL to SYD $299 roundtrip")
        assert origin == "AKL"
        assert dest == "SYD"

    def test_from_to_pattern(self):
        origin, dest = AirportLookup.extract_route("Flights from Auckland to London")
        assert origin == "AKL"
        assert dest == "LHR"

    def test_destination_from_origin(self):
        origin, dest = AirportLookup.extract_route("Tokyo from Auckland $599")
        assert origin == "AKL"
        assert dest == "NRT"

    def test_code_dash_code(self):
        origin, dest = AirportLookup.extract_route("AKL-SYD $299 return flights")
        assert origin == "AKL"
        assert dest == "SYD"

    def test_code_space_dash_code(self):
        origin, dest = AirportLookup.extract_route("AKL - SYD $299 return flights")
        assert origin == "AKL"
        assert dest == "SYD"

    def test_nonstop_from_to(self):
        origin, dest = AirportLookup.extract_route("Nonstop from Los Angeles to Tokyo for $499")
        assert origin == "LAX"
        assert dest == "NRT"


class TestCityListsRejected:
    """City lists and incidental mentions should NOT produce routes."""

    def test_comma_separated_three_cities(self):
        origin, dest = AirportLookup.extract_route("Cheap flights from Auckland, Wellington, Christchurch")
        assert origin is None
        assert dest is None

    def test_comma_separated_four_cities(self):
        origin, dest = AirportLookup.extract_route("Deals: Auckland, Sydney, Melbourne, Brisbane")
        assert origin is None
        assert dest is None

    def test_two_cities_no_structure(self):
        """Two cities mentioned without any route indicator should not extract."""
        origin, dest = AirportLookup.extract_route("Auckland and Dunedin flights sale")
        assert origin is None
        assert dest is None

    def test_single_city(self):
        origin, dest = AirportLookup.extract_route("Auckland deals from $32")
        assert origin is None
        assert dest is None

    def test_general_title_with_dash(self):
        """Hyphens in general titles should not create phantom routes."""
        origin, dest = AirportLookup.extract_route("Great deals - Auckland travelers rejoice")
        assert origin is None
        assert dest is None

    def test_city_in_source_attribution(self):
        """Cities mentioned as source attribution, not route."""
        origin, dest = AirportLookup.extract_route("Flight sale announced by Auckland airport")
        assert origin is None
        assert dest is None

    def test_slash_separated_cities(self):
        origin, dest = AirportLookup.extract_route("Auckland/Wellington/Christchurch fare sale")
        # These might match as 3 locations with commas between — depends on find_locations
        # At minimum should not create a false route
        # 3+ locations without route structure = no route
        assert origin is None or dest is None


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_string(self):
        origin, dest = AirportLookup.extract_route("")
        assert origin is None
        assert dest is None

    def test_no_locations(self):
        origin, dest = AirportLookup.extract_route("Great flight deals this summer")
        assert origin is None
        assert dest is None

    def test_same_origin_destination(self):
        """Same city mentioned with 'to' should not produce a route."""
        origin, dest = AirportLookup.extract_route("Auckland to Auckland flights")
        assert origin is None
        assert dest is None

    def test_price_not_mistaken_for_location(self):
        """$599 should not be parsed as a location."""
        origin, dest = AirportLookup.extract_route("$599 flights to Tokyo")
        # Only one location (Tokyo) + price, no origin
        # This may or may not extract depending on whether $599 matches anything
        # At minimum, if it extracts, the origin should be a real airport
        if origin is not None:
            assert len(origin) == 3 and origin.isalpha()

    def test_hyphen_in_compound_word(self):
        """Hyphens in compound words should not trigger route extraction."""
        origin, dest = AirportLookup.extract_route("Non-stop Auckland to London")
        assert origin == "AKL"
        assert dest == "LHR"
