"""Tests for Seats.aero client: program IDs, direct flight detection, and search URL construction."""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the modules under test directly (no app context needed)
from app.services.seats_aero import (
    AwardResult,
    CABIN_API_NAMES,
    CABIN_MAP,
    SearchResponse,
    SeatsAeroClient,
    hash_results,
)
from app.models.award import AwardProgram


def _make_mock_client(response_data: dict) -> tuple[SeatsAeroClient, AsyncMock]:
    """Create a SeatsAeroClient with a mocked HTTP transport.

    Returns (client, mock_http) so tests can inspect call args.
    """
    client = SeatsAeroClient(api_key="test")
    mock_http = AsyncMock()
    mock_http.is_closed = False  # Prevent _get_client from replacing our mock
    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()
    mock_http.get = AsyncMock(return_value=mock_response)
    client._client = mock_http
    return client, mock_http


# ---------------------------------------------------------------------------
# Bug 2: Program ID mapping
# ---------------------------------------------------------------------------

class TestAwardProgramEnum:
    """Verify that AwardProgram enum values match Seats.aero Source identifiers."""

    def test_qantas_value(self):
        assert AwardProgram.QANTAS.value == "qantas"

    def test_flying_blue_value(self):
        assert AwardProgram.FLYING_BLUE.value == "flyingblue"

    def test_american_value(self):
        assert AwardProgram.AMERICAN.value == "american"

    def test_virgin_atlantic_value(self):
        assert AwardProgram.VIRGIN_ATLANTIC.value == "virginatlantic"

    def test_united_value(self):
        assert AwardProgram.UNITED.value == "united"

    def test_aeroplan_value(self):
        assert AwardProgram.AEROPLAN.value == "aeroplan"

    def test_velocity_value(self):
        assert AwardProgram.VELOCITY.value == "velocity"

    def test_alaska_value(self):
        assert AwardProgram.ALASKA.value == "alaska"

    def test_additional_programs_exist(self):
        """Verify all required additional programs are present."""
        expected = {
            "smiles", "delta", "emirates", "etihad", "eurobonus",
            "jetblue", "qatar", "singapore", "saudia", "connectmiles",
            "lifemiles", "asiamiles", "alaska", "united", "aeroplan",
            "velocity",
        }
        actual_values = {p.value for p in AwardProgram}
        assert expected.issubset(actual_values), (
            f"Missing programs: {expected - actual_values}"
        )

    def test_no_old_wrong_values(self):
        """Ensure the old incorrect values are gone."""
        all_values = {p.value for p in AwardProgram}
        assert "qantas_ff" not in all_values
        assert "flying_blue" not in all_values
        assert "aadvantage" not in all_values
        assert "virgin_atlantic" not in all_values


# ---------------------------------------------------------------------------
# Bug 3: Direct flight detection
# ---------------------------------------------------------------------------

class TestDirectFlightDetection:
    """Verify per-cabin direct flight flag parsing."""

    def _make_api_item(
        self,
        cabin_code: str = "J",
        available: bool = True,
        direct: bool = True,
        miles: str = "80000",
        seats: int = 2,
        route: str = "SYD-LAX",
        source: str = "qantas",
        airlines: str = "QF",
    ) -> dict:
        """Build a mock Seats.aero /search response item."""
        return {
            "ID": "test-id",
            "Route": route,
            "Date": "2026-03-15",
            f"{cabin_code}Available": available,
            f"{cabin_code}MileageCost": miles,
            f"{cabin_code}Direct": direct,
            f"{cabin_code}RemainingSeats": seats,
            f"{cabin_code}Airlines": airlines,
            "Source": source,
        }

    @pytest.mark.asyncio
    async def test_business_direct_true(self):
        """JDirect=True should set is_direct=True for business cabin."""
        item = self._make_api_item(cabin_code="J", direct=True)
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="business"
        )
        assert len(result.results) == 1
        assert result.results[0].is_direct is True

    @pytest.mark.asyncio
    async def test_business_direct_false(self):
        """JDirect=False should set is_direct=False for business cabin."""
        item = self._make_api_item(cabin_code="J", direct=False)
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="business"
        )
        assert len(result.results) == 1
        assert result.results[0].is_direct is False

    @pytest.mark.asyncio
    async def test_economy_direct_flag(self):
        """YDirect should be used for economy cabin."""
        item = self._make_api_item(cabin_code="Y", direct=True, miles="45000")
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="economy"
        )
        assert len(result.results) == 1
        assert result.results[0].is_direct is True

    @pytest.mark.asyncio
    async def test_first_class_direct_flag(self):
        """FDirect should be used for first class cabin."""
        item = self._make_api_item(cabin_code="F", direct=False, miles="120000")
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="first"
        )
        assert len(result.results) == 1
        assert result.results[0].is_direct is False

    @pytest.mark.asyncio
    async def test_premium_economy_direct_flag(self):
        """WDirect should be used for premium economy cabin."""
        item = self._make_api_item(cabin_code="W", direct=True, miles="60000")
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="premium_economy"
        )
        assert len(result.results) == 1
        assert result.results[0].is_direct is True

    @pytest.mark.asyncio
    async def test_direct_only_filter_uses_cabin_flag(self):
        """direct_only=True should filter using the cabin-specific Direct flag."""
        direct_item = self._make_api_item(cabin_code="J", direct=True, miles="80000")
        connecting_item = self._make_api_item(cabin_code="J", direct=False, miles="70000")
        connecting_item["ID"] = "test-id-2"
        client, _ = _make_mock_client({"data": [direct_item, connecting_item], "count": 2})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31",
            cabin="business", direct_only=True,
        )
        assert len(result.results) == 1
        assert result.results[0].is_direct is True
        assert result.results[0].miles == 80000


# ---------------------------------------------------------------------------
# Bug 1: Search URL construction
# ---------------------------------------------------------------------------

class TestSearchURLConstruction:
    """Verify the /search endpoint is used with correct parameters."""

    @pytest.mark.asyncio
    async def test_uses_search_endpoint(self):
        """Client should call /search, not /availability."""
        item = {
            "ID": "test-id",
            "Route": "SYD-LAX",
            "Date": "2026-03-15",
            "JAvailable": True,
            "JMileageCost": "80000",
            "JDirect": True,
            "JRemainingSeats": 2,
            "JAirlines": "QF",
            "Source": "qantas",
        }
        client, mock_http = _make_mock_client({"data": [item], "count": 1})

        await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="business"
        )

        mock_http.get.assert_called_once()
        call_args = mock_http.get.call_args
        assert call_args[0][0] == "/search"

    @pytest.mark.asyncio
    async def test_uses_sources_parameter(self):
        """Program filter should use 'sources' (plural), not 'source'."""
        client, mock_http = _make_mock_client({"data": [], "count": 0})

        await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31",
            cabin="business", program="qantas",
        )

        call_args = mock_http.get.call_args
        params = call_args[1]["params"]
        assert "sources" in params
        assert params["sources"] == "qantas"
        assert "source" not in params

    @pytest.mark.asyncio
    async def test_includes_order_by(self):
        """Params should include order_by=lowest_mileage."""
        client, mock_http = _make_mock_client({"data": [], "count": 0})

        await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31",
        )

        call_args = mock_http.get.call_args
        params = call_args[1]["params"]
        assert params["order_by"] == "lowest_mileage"

    @pytest.mark.asyncio
    async def test_includes_cabin_parameter(self):
        """Params should include the cabin filter for server-side filtering."""
        client, mock_http = _make_mock_client({"data": [], "count": 0})

        await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="business",
        )

        call_args = mock_http.get.call_args
        params = call_args[1]["params"]
        assert params["cabin"] == "business"

    @pytest.mark.asyncio
    async def test_cabin_api_name_premium_economy(self):
        """premium_economy should map to 'premiumeconomy' for the API."""
        client, mock_http = _make_mock_client({"data": [], "count": 0})

        await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="premium_economy",
        )

        call_args = mock_http.get.call_args
        params = call_args[1]["params"]
        assert params["cabin"] == "premiumeconomy"

    @pytest.mark.asyncio
    async def test_no_sources_when_no_program(self):
        """When program is None, 'sources' should not be in params."""
        client, mock_http = _make_mock_client({"data": [], "count": 0})

        await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31",
        )

        call_args = mock_http.get.call_args
        params = call_args[1]["params"]
        assert "sources" not in params

    @pytest.mark.asyncio
    async def test_multi_program_sources(self):
        """Comma-separated programs should be passed as-is to sources."""
        client, mock_http = _make_mock_client({"data": [], "count": 0})

        await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31",
            program="qantas,united,american",
        )

        call_args = mock_http.get.call_args
        params = call_args[1]["params"]
        assert params["sources"] == "qantas,united,american"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestResponseParsing:
    """Test that the /search response format is parsed correctly."""

    @pytest.mark.asyncio
    async def test_parses_route_string(self):
        """Route in 'SYD-LAX' format should be split into origin/destination."""
        item = {
            "ID": "test-id",
            "Route": "AKL-SYD",
            "Date": "2026-03-15",
            "JAvailable": True,
            "JMileageCost": "80000",
            "JDirect": True,
            "JRemainingSeats": 2,
            "JAirlines": "QF",
            "Source": "qantas",
        }
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "AKL", "SYD", "2026-03-01", "2026-03-31", cabin="business"
        )
        assert len(result.results) == 1
        assert result.results[0].origin == "AKL"
        assert result.results[0].destination == "SYD"

    @pytest.mark.asyncio
    async def test_parses_string_mileage_cost(self):
        """MileageCost comes as a string from the API and should be parsed to int."""
        item = {
            "ID": "test-id",
            "Route": "SYD-LAX",
            "Date": "2026-03-15",
            "JAvailable": True,
            "JMileageCost": "80000",
            "JDirect": False,
            "JRemainingSeats": 2,
            "JAirlines": "QF",
            "Source": "qantas",
        }
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="business"
        )
        assert result.results[0].miles == 80000

    @pytest.mark.asyncio
    async def test_extracts_cabin_specific_airlines(self):
        """Airlines field should come from the cabin-specific key (e.g. JAirlines)."""
        item = {
            "ID": "test-id",
            "Route": "SYD-LAX",
            "Date": "2026-03-15",
            "JAvailable": True,
            "JMileageCost": "80000",
            "JDirect": False,
            "JRemainingSeats": 2,
            "JAirlines": "QF,AA",
            "Source": "qantas",
        }
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="business"
        )
        assert result.results[0].airline == "QF,AA"

    @pytest.mark.asyncio
    async def test_skips_unavailable_cabin(self):
        """Items where the cabin is not available should be filtered out."""
        item = {
            "ID": "test-id",
            "Route": "SYD-LAX",
            "Date": "2026-03-15",
            "JAvailable": False,
            "JMileageCost": "80000",
            "JDirect": True,
            "JRemainingSeats": 0,
            "JAirlines": "QF",
            "Source": "qantas",
        }
        client, _ = _make_mock_client({"data": [item], "count": 1})

        result = await client.search_availability(
            "SYD", "LAX", "2026-03-01", "2026-03-31", cabin="business"
        )
        assert len(result.results) == 0


# ---------------------------------------------------------------------------
# Hash results (unchanged, but verify still works)
# ---------------------------------------------------------------------------

class TestHashResults:
    """Verify hash_results still produces deterministic hashes."""

    def test_same_results_same_hash(self):
        results = [
            AwardResult("SYD", "LAX", "2026-03-15", "qantas", "business", 80000, seats_available=2),
        ]
        assert hash_results(results) == hash_results(results)

    def test_different_results_different_hash(self):
        r1 = [AwardResult("SYD", "LAX", "2026-03-15", "qantas", "business", 80000, seats_available=2)]
        r2 = [AwardResult("SYD", "LAX", "2026-03-15", "qantas", "business", 90000, seats_available=2)]
        assert hash_results(r1) != hash_results(r2)

    def test_order_independent(self):
        a = AwardResult("SYD", "LAX", "2026-03-15", "qantas", "business", 80000, seats_available=2)
        b = AwardResult("SYD", "LAX", "2026-03-16", "united", "business", 70000, seats_available=1)
        assert hash_results([a, b]) == hash_results([b, a])
