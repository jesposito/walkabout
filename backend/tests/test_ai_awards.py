"""Tests for AI award intelligence features.

Tests prompt construction and response parsing by mocking AIService.complete.
Run with: python3 -m pytest backend/tests/test_ai_awards.py -v --noconftest
"""

import json
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai_awards import (
    find_patterns,
    evaluate_miles,
    estimate_patterns,
    estimate_mile_value,
    _build_observation_summary,
    _build_mile_value_context,
    _parse_json_response,
)


def make_search(**overrides):
    """Create a mock TrackedAwardSearch object with sensible defaults."""
    search = MagicMock()
    search.id = overrides.get("id", 1)
    search.origin = overrides.get("origin", "AKL")
    search.destination = overrides.get("destination", "NRT")
    search.program = overrides.get("program", "united")
    search.date_start = overrides.get("date_start", datetime(2026, 6, 1))
    search.date_end = overrides.get("date_end", datetime(2026, 6, 30))
    search.cabin_class = overrides.get("cabin_class", "business")
    search.min_seats = overrides.get("min_seats", 2)
    search.direct_only = overrides.get("direct_only", False)
    search.is_active = overrides.get("is_active", True)
    search.name = overrides.get("name", "AKL-NRT business")
    return search


def make_observation(**overrides):
    """Create a mock AwardObservation object with sensible defaults."""
    obs = MagicMock()
    obs.id = overrides.get("id", 1)
    obs.search_id = overrides.get("search_id", 1)
    obs.observed_at = overrides.get("observed_at", datetime(2026, 5, 15, 10, 30))
    obs.is_changed = overrides.get("is_changed", True)
    obs.programs_with_availability = overrides.get("programs_with_availability", ["united", "aeroplan"])
    obs.best_economy_miles = overrides.get("best_economy_miles", 35000)
    obs.best_business_miles = overrides.get("best_business_miles", 75000)
    obs.best_first_miles = overrides.get("best_first_miles", None)
    obs.total_options = overrides.get("total_options", 12)
    obs.max_seats_available = overrides.get("max_seats_available", 4)
    return obs


class TestBuildObservationSummary:
    def test_basic_summary(self):
        search = make_search()
        summary = _build_observation_summary(search, [])
        assert "AKL" in summary
        assert "NRT" in summary
        assert "business" in summary
        assert "united" in summary

    def test_summary_with_observations(self):
        search = make_search()
        obs = make_observation()
        summary = _build_observation_summary(search, [obs])
        assert "1 data points" in summary
        assert "75,000" in summary or "75000" in summary
        assert "united" in summary
        assert "aeroplan" in summary
        assert "12" in summary  # total_options

    def test_summary_no_program(self):
        search = make_search(program=None)
        summary = _build_observation_summary(search, [])
        assert "all programs" in summary

    def test_summary_with_date_range(self):
        search = make_search()
        summary = _build_observation_summary(search, [])
        assert "2026-06-01" in summary
        assert "2026-06-30" in summary

    def test_summary_min_seats(self):
        search = make_search(min_seats=3)
        summary = _build_observation_summary(search, [])
        assert "3" in summary

    def test_summary_direct_only(self):
        search = make_search(direct_only=True)
        summary = _build_observation_summary(search, [])
        assert "Direct flights only: yes" in summary

    def test_summary_no_observations(self):
        search = make_search()
        summary = _build_observation_summary(search, [])
        assert "No observation history available yet" in summary

    def test_summary_multiple_observations(self):
        search = make_search()
        obs1 = make_observation(id=1, observed_at=datetime(2026, 5, 15, 10, 0), total_options=12)
        obs2 = make_observation(id=2, observed_at=datetime(2026, 5, 16, 10, 0), total_options=8)
        summary = _build_observation_summary(search, [obs1, obs2])
        assert "2 data points" in summary


class TestBuildMileValueContext:
    def test_basic_context(self):
        context = _build_mile_value_context("AKL", "NRT", 80000, "united", "business")
        assert "AKL" in context
        assert "NRT" in context
        assert "80,000" in context
        assert "united" in context
        assert "business" in context

    def test_context_with_cash_price(self):
        context = _build_mile_value_context("AKL", "NRT", 80000, "united", "business", cash_price=3500.00)
        assert "3,500.00" in context
        assert "cpp" in context  # cents per mile

    def test_context_without_cash_price(self):
        context = _build_mile_value_context("AKL", "NRT", 80000, "united", "business")
        assert "not provided" in context

    def test_cents_per_mile_calculation(self):
        context = _build_mile_value_context("AKL", "NRT", 100000, "united", "business", cash_price=2000.00)
        assert "2.00 cpp" in context  # 2000/100000 * 100 = 2.0


class TestParseJsonResponse:
    def test_plain_json(self):
        result = _parse_json_response('{"rating": "good"}')
        assert result["rating"] == "good"

    def test_json_with_code_fence(self):
        result = _parse_json_response('```json\n{"rating": "good"}\n```')
        assert result["rating"] == "good"

    def test_json_with_generic_fence(self):
        result = _parse_json_response('```\n{"rating": "good"}\n```')
        assert result["rating"] == "good"

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("This is not JSON at all")


class TestFindPatterns:
    @pytest.mark.asyncio
    async def test_successful_analysis(self):
        search = make_search()
        obs = [make_observation()]
        mock_response = json.dumps({
            "sweet_spots": [
                {"program": "united", "insight": "United consistently shows 75K business class."},
                {"program": "aeroplan", "insight": "Aeroplan sometimes offers lower rates at 60K."},
            ],
            "timing": "Availability peaks mid-week, especially Tuesday-Thursday.",
            "trend": "stable",
            "recommendation": "Book through Aeroplan when available for best value. Check Tuesday mornings for new releases.",
            "best_value_program": "aeroplan",
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 200,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            result = await find_patterns(search, obs)

        assert len(result["sweet_spots"]) == 2
        assert result["trend"] == "stable"
        assert result["best_value_program"] == "aeroplan"
        assert "Aeroplan" in result["recommendation"] or "aeroplan" in result["recommendation"]
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_no_observations(self):
        search = make_search()
        mock_response = json.dumps({
            "sweet_spots": [],
            "timing": "No data available yet.",
            "trend": "insufficient_data",
            "recommendation": "Poll the search a few times to gather data before analysis.",
            "best_value_program": None,
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 500,
                "cost_est_usd": 0.002,
            }
            result = await find_patterns(search, [])

        assert result["trend"] == "insufficient_data"
        assert result["sweet_spots"] == []

    @pytest.mark.asyncio
    async def test_malformed_response_fallback(self):
        search = make_search()
        obs = [make_observation()]
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value="The data shows good availability generally.")
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 200,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            result = await find_patterns(search, obs)

        assert result["sweet_spots"] == []
        assert result["trend"] == "insufficient_data"
        assert "good availability" in result["timing"]
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_prompt_includes_search_details(self):
        search = make_search(origin="SYD", destination="LHR", program="qantas")
        obs = [make_observation(best_business_miles=90000)]
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps({
                "sweet_spots": [],
                "timing": "",
                "trend": "stable",
                "recommendation": "",
                "best_value_program": None,
            })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = capture_prompt
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 200,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            await find_patterns(search, obs)

        assert "SYD" in captured_prompt
        assert "LHR" in captured_prompt
        assert "qantas" in captured_prompt


class TestEvaluateMiles:
    @pytest.mark.asyncio
    async def test_successful_evaluation(self):
        mock_response = json.dumps({
            "cents_per_mile": 2.8,
            "rating": "good",
            "reasoning": "At 2.8 cents per mile, this is solid value for United MileagePlus on a premium cabin.",
            "benchmark": "United miles are typically valued at 1.2-1.8 cpp, so 2.8 cpp is above average.",
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 80,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = await evaluate_miles(
                origin="AKL",
                destination="NRT",
                miles=80000,
                program="united",
                cabin="business",
                cash_price=3500.00,
            )

        assert result["cents_per_mile"] == 2.8
        assert result["rating"] == "good"
        assert "2.8" in result["reasoning"]
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_without_cash_price(self):
        mock_response = json.dumps({
            "cents_per_mile": 1.5,
            "rating": "fair",
            "reasoning": "Without a cash price comparison, estimating based on typical fares.",
            "benchmark": "United business typically goes for $4000-8000 on this route.",
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 60,
                "output_tokens_est": 300,
                "cost_est_usd": 0.001,
            }
            result = await evaluate_miles(
                origin="AKL",
                destination="NRT",
                miles=80000,
                program="united",
                cabin="business",
            )

        assert result["rating"] == "fair"
        assert result["cents_per_mile"] == 1.5

    @pytest.mark.asyncio
    async def test_malformed_response_fallback(self):
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value="That seems like a decent deal overall.")
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 80,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = await evaluate_miles(
                origin="AKL",
                destination="NRT",
                miles=80000,
                program="united",
                cabin="business",
            )

        assert result["cents_per_mile"] == 0
        assert result["rating"] == "fair"
        assert "decent deal" in result["reasoning"]
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_prompt_includes_details(self):
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps({
                "cents_per_mile": 2.0,
                "rating": "good",
                "reasoning": "Good value.",
                "benchmark": "Average.",
            })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = capture_prompt
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 80,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            await evaluate_miles(
                origin="SYD",
                destination="LAX",
                miles=60000,
                program="qantas",
                cabin="economy",
                cash_price=1200.00,
            )

        assert "SYD" in captured_prompt
        assert "LAX" in captured_prompt
        assert "60,000" in captured_prompt
        assert "qantas" in captured_prompt
        assert "economy" in captured_prompt
        assert "1,200.00" in captured_prompt


class TestEstimateFunctions:
    def test_estimate_patterns(self):
        search = make_search()
        obs = [make_observation()]
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 200,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            result = estimate_patterns(search, obs)

        assert "input_tokens_est" in result
        assert "output_tokens_est" in result
        assert "cost_est_usd" in result

    def test_estimate_patterns_no_observations(self):
        search = make_search()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 500,
                "cost_est_usd": 0.002,
            }
            result = estimate_patterns(search, [])

        assert "input_tokens_est" in result

    def test_estimate_mile_value(self):
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 80,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = estimate_mile_value(
                origin="AKL",
                destination="NRT",
                miles=80000,
                program="united",
                cabin="business",
            )

        assert "input_tokens_est" in result
        assert "output_tokens_est" in result
        assert "cost_est_usd" in result

    def test_estimate_mile_value_with_cash_price(self):
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 90,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = estimate_mile_value(
                origin="AKL",
                destination="NRT",
                miles=80000,
                program="united",
                cabin="business",
                cash_price=3500.00,
            )

        assert "input_tokens_est" in result
