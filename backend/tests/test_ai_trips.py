"""Tests for AI trip intelligence features.

Tests prompt construction and response parsing by mocking AIService.complete.
Run with: python3 -m pytest backend/tests/test_ai_trips.py -v --noconftest
"""

import json
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai_trips import (
    name_trip,
    check_feasibility,
    suggest_destinations,
    estimate_name_trip,
    estimate_feasibility,
    _build_trip_summary,
    _parse_json_response,
)


def make_trip(**overrides):
    """Create a mock TripPlan object with sensible defaults."""
    trip = MagicMock()
    trip.id = overrides.get("id", 1)
    trip.name = overrides.get("name", "Test Trip")
    trip.origins = overrides.get("origins", ["AKL"])
    trip.destinations = overrides.get("destinations", ["NRT"])
    trip.destination_types = overrides.get("destination_types", [])
    trip.legs = overrides.get("legs", [])
    trip.available_from = overrides.get("available_from", datetime(2026, 3, 1))
    trip.available_to = overrides.get("available_to", datetime(2026, 4, 30))
    trip.trip_duration_min = overrides.get("trip_duration_min", 7)
    trip.trip_duration_max = overrides.get("trip_duration_max", 14)
    trip.budget_max = overrides.get("budget_max", 3000)
    trip.budget_currency = overrides.get("budget_currency", "NZD")
    trip.travelers_adults = overrides.get("travelers_adults", 2)
    trip.travelers_children = overrides.get("travelers_children", 0)
    trip.cabin_classes = overrides.get("cabin_classes", ["economy"])
    trip.notes = overrides.get("notes", None)
    return trip


class TestBuildTripSummary:
    def test_basic_trip_summary(self):
        trip = make_trip()
        summary = _build_trip_summary(trip)
        assert "AKL" in summary
        assert "NRT" in summary
        assert "3000" in summary
        assert "NZD" in summary
        assert "2 adult(s)" in summary

    def test_no_destination(self):
        trip = make_trip(destinations=[])
        summary = _build_trip_summary(trip)
        assert "not specified (open to anywhere)" in summary

    def test_no_budget(self):
        trip = make_trip(budget_max=None)
        summary = _build_trip_summary(trip)
        assert "not specified" in summary

    def test_with_notes(self):
        trip = make_trip(notes="Anniversary trip")
        summary = _build_trip_summary(trip)
        assert "Anniversary trip" in summary

    def test_with_legs(self):
        trip = make_trip(
            legs=[
                {"origin": "AKL", "destination": "SIN", "date_start": "2026-03-01", "date_end": None},
                {"origin": "SIN", "destination": "NRT", "date_start": None, "date_end": None},
            ]
        )
        summary = _build_trip_summary(trip)
        assert "AKL -> SIN" in summary
        assert "SIN -> NRT" in summary

    def test_with_destination_types(self):
        trip = make_trip(destination_types=["beach", "tropical"])
        summary = _build_trip_summary(trip)
        assert "beach" in summary
        assert "tropical" in summary


class TestParseJsonResponse:
    def test_plain_json(self):
        result = _parse_json_response('{"name": "Adventure"}')
        assert result["name"] == "Adventure"

    def test_json_with_code_fence(self):
        result = _parse_json_response('```json\n{"name": "Adventure"}\n```')
        assert result["name"] == "Adventure"

    def test_json_with_generic_fence(self):
        result = _parse_json_response('```\n{"name": "Adventure"}\n```')
        assert result["name"] == "Adventure"

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("This is not JSON")


class TestNameTrip:
    @pytest.mark.asyncio
    async def test_successful_naming(self):
        trip = make_trip(destinations=[])
        mock_response = json.dumps({
            "name": "Shot in the Dark",
            "vibe": "An open-ended adventure to wherever the deals take you."
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 150,
                "cost_est_usd": 0.001,
            }
            result = await name_trip(trip)

        assert result["name"] == "Shot in the Dark"
        assert "open-ended adventure" in result["vibe"]
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_malformed_response_fallback(self):
        trip = make_trip()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value="I think a great name would be Tokyo Express!")
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 150,
                "cost_est_usd": 0.001,
            }
            result = await name_trip(trip)

        # Should fall back gracefully
        assert result["name"] == "Untitled Trip"
        assert "Tokyo Express" in result["vibe"]
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_prompt_includes_trip_details(self):
        trip = make_trip(origins=["MEL"], destinations=["HKG"], budget_max=5000)
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps({"name": "Test", "vibe": "Test vibe"})

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = capture_prompt
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 150,
                "cost_est_usd": 0.001,
            }
            await name_trip(trip)

        assert "MEL" in captured_prompt
        assert "HKG" in captured_prompt
        assert "5000" in captured_prompt


class TestCheckFeasibility:
    @pytest.mark.asyncio
    async def test_successful_check(self):
        trip = make_trip()
        mock_response = json.dumps({
            "verdict": "This trip looks very doable.",
            "reasoning": "NZD 3000 for economy flights from AKL to NRT is reasonable. March-April is shoulder season in Japan.",
            "confidence": "high",
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 120,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = await check_feasibility(trip)

        assert "doable" in result["verdict"]
        assert result["confidence"] == "high"
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_low_budget_response(self):
        trip = make_trip(budget_max=200, cabin_classes=["business"])
        mock_response = json.dumps({
            "verdict": "This budget is not realistic for business class.",
            "reasoning": "Business class from AKL to NRT typically costs NZD 5000-10000 per person.",
            "confidence": "high",
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 120,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = await check_feasibility(trip)

        assert "not realistic" in result["verdict"]

    @pytest.mark.asyncio
    async def test_malformed_response_fallback(self):
        trip = make_trip()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value="Looks good to me!")
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 120,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = await check_feasibility(trip)

        assert result["verdict"] == "Looks good to me!"
        assert result["confidence"] == "low"


class TestSuggestDestinations:
    @pytest.mark.asyncio
    async def test_successful_suggestions(self):
        mock_response = json.dumps({
            "suggestions": [
                {"airport": "NRT", "city": "Tokyo", "reasoning": "Great cherry blossom season in March-April."},
                {"airport": "BKK", "city": "Bangkok", "reasoning": "Budget-friendly destination with warm weather."},
                {"airport": "SIN", "city": "Singapore", "reasoning": "Easy direct flights, great food scene."},
            ]
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 80,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            result = await suggest_destinations(
                origins=["AKL"],
                dates={"available_from": "2026-03-01", "available_to": "2026-04-30"},
                budget={"budget_max": 3000, "budget_currency": "NZD"},
            )

        assert len(result["suggestions"]) == 3
        assert result["suggestions"][0]["airport"] == "NRT"
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_empty_response_fallback(self):
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value="I can't make suggestions right now.")
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 80,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            result = await suggest_destinations(
                origins=["AKL"],
                dates={},
                budget={},
            )

        assert result["suggestions"] == []

    @pytest.mark.asyncio
    async def test_prompt_includes_all_params(self):
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps({"suggestions": []})

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = capture_prompt
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 80,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            await suggest_destinations(
                origins=["AKL", "CHC"],
                dates={"available_from": "2026-06-01", "duration_min": 5, "duration_max": 10},
                budget={"budget_max": 5000, "budget_currency": "AUD"},
                cabin_classes=["business"],
                travelers={"adults": 1, "children": 2},
            )

        assert "AKL" in captured_prompt
        assert "CHC" in captured_prompt
        assert "5000" in captured_prompt
        assert "AUD" in captured_prompt
        assert "business" in captured_prompt
        assert "1 adult(s)" in captured_prompt
        assert "2 child(ren)" in captured_prompt


class TestEstimateFunctions:
    def test_estimate_name_trip(self):
        trip = make_trip()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 150,
                "cost_est_usd": 0.001,
            }
            result = estimate_name_trip(trip)

        assert "input_tokens_est" in result
        assert "output_tokens_est" in result
        assert "cost_est_usd" in result

    def test_estimate_feasibility(self):
        trip = make_trip()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 120,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = estimate_feasibility(trip)

        assert "input_tokens_est" in result
        assert "output_tokens_est" in result
        assert "cost_est_usd" in result
