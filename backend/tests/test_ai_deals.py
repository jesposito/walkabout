"""Tests for AI deal intelligence features.

Tests prompt construction and response parsing by mocking AIService.complete.
Run with: python3 -m pytest backend/tests/test_ai_deals.py -v --noconftest
"""

import json
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai_deals import (
    generate_digest,
    explain_deal,
    review_settings,
    estimate_digest,
    estimate_explain,
    estimate_settings_review,
    _build_deals_summary,
    _build_deal_detail,
    _build_settings_summary,
    _parse_json_response,
)


def make_deal(**overrides):
    """Create a mock Deal object with sensible defaults."""
    deal = MagicMock()
    deal.id = overrides.get("id", 1)
    deal.raw_title = overrides.get("raw_title", "AKL to NRT from $499 on Air NZ")
    deal.parsed_origin = overrides.get("parsed_origin", "AKL")
    deal.parsed_destination = overrides.get("parsed_destination", "NRT")
    deal.parsed_price = overrides.get("parsed_price", 499)
    deal.parsed_currency = overrides.get("parsed_currency", "NZD")
    deal.parsed_airline = overrides.get("parsed_airline", "Air New Zealand")
    deal.parsed_cabin_class = overrides.get("parsed_cabin_class", "economy")
    deal.deal_rating = overrides.get("deal_rating", 35.0)
    deal.rating_label = overrides.get("rating_label", "Hot Deal")
    deal.market_price = overrides.get("market_price", 770.0)
    deal.market_currency = overrides.get("market_currency", "NZD")
    deal.source = MagicMock()
    deal.source.value = overrides.get("source", "secret_flying")
    deal.published_at = overrides.get("published_at", datetime(2026, 2, 5, 10, 30))
    deal.is_relevant = overrides.get("is_relevant", True)
    deal.relevance_reason = overrides.get("relevance_reason", "Local deal")
    return deal


def make_settings(**overrides):
    """Create a mock UserSettings object with sensible defaults."""
    settings = MagicMock()
    settings.home_airport = overrides.get("home_airport", "AKL")
    settings.home_airports = overrides.get("home_airports", ["AKL", "CHC"])
    settings.home_region = overrides.get("home_region", "Oceania")
    settings.watched_destinations = overrides.get("watched_destinations", ["NRT", "SIN", "BKK"])
    settings.watched_regions = overrides.get("watched_regions", ["Asia"])
    settings.preferred_currency = overrides.get("preferred_currency", "NZD")
    settings.notifications_enabled = overrides.get("notifications_enabled", True)
    settings.notification_provider = overrides.get("notification_provider", "ntfy_sh")
    settings.deal_cooldown_minutes = overrides.get("deal_cooldown_minutes", 60)
    settings.daily_digest_enabled = overrides.get("daily_digest_enabled", False)
    settings.ai_provider = overrides.get("ai_provider", "anthropic")
    settings.ai_model = overrides.get("ai_model", "claude-3-haiku")
    settings.seats_aero_api_key = overrides.get("seats_aero_api_key", None)
    settings.serpapi_key = overrides.get("serpapi_key", "some-key")
    settings.skyscanner_api_key = overrides.get("skyscanner_api_key", None)
    settings.amadeus_client_id = overrides.get("amadeus_client_id", None)
    return settings


class TestParseJsonResponse:
    def test_plain_json(self):
        result = _parse_json_response('{"summary": "Great deals today"}')
        assert result["summary"] == "Great deals today"

    def test_json_with_code_fence(self):
        result = _parse_json_response('```json\n{"summary": "Great deals"}\n```')
        assert result["summary"] == "Great deals"

    def test_json_with_generic_fence(self):
        result = _parse_json_response('```\n{"summary": "Great deals"}\n```')
        assert result["summary"] == "Great deals"

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_json_response("This is not JSON")


class TestBuildDealsSummary:
    def test_basic_summary(self):
        deals = [make_deal(), make_deal(id=2, parsed_origin="SYD", parsed_destination="LAX", parsed_price=799)]
        summary = _build_deals_summary(deals)
        assert "AKL -> NRT" in summary
        assert "SYD -> LAX" in summary
        assert "499" in summary
        assert "799" in summary

    def test_deal_with_no_route(self):
        deal = make_deal(parsed_origin=None, parsed_destination=None)
        summary = _build_deals_summary([deal])
        assert "AKL to NRT" in summary  # Falls back to raw_title

    def test_deal_with_rating(self):
        deal = make_deal(deal_rating=35.0, rating_label="Hot Deal")
        summary = _build_deals_summary([deal])
        assert "35%" in summary
        assert "Hot Deal" in summary

    def test_empty_deals(self):
        summary = _build_deals_summary([])
        assert summary == ""


class TestBuildDealDetail:
    def test_full_detail(self):
        deal = make_deal()
        detail = _build_deal_detail(deal)
        assert "AKL to NRT" in detail
        assert "AKL" in detail
        assert "NRT" in detail
        assert "499" in detail
        assert "NZD" in detail
        assert "Air New Zealand" in detail
        assert "economy" in detail
        assert "35%" in detail
        assert "Hot Deal" in detail

    def test_minimal_detail(self):
        deal = make_deal(
            parsed_origin=None,
            parsed_destination=None,
            parsed_price=None,
            parsed_currency=None,
            parsed_airline=None,
            parsed_cabin_class=None,
            deal_rating=None,
            rating_label=None,
            market_price=None,
            market_currency=None,
        )
        detail = _build_deal_detail(deal)
        assert "Title:" in detail
        assert "AKL to NRT" in detail


class TestBuildSettingsSummary:
    def test_full_settings(self):
        settings = make_settings()
        summary = _build_settings_summary(settings)
        assert "AKL" in summary
        assert "CHC" in summary
        assert "Oceania" in summary
        assert "NRT" in summary
        assert "NZD" in summary
        assert "enabled" in summary
        assert "anthropic" in summary
        assert "SerpAPI" in summary

    def test_minimal_settings(self):
        settings = make_settings(
            home_airports=[],
            home_airport=None,
            watched_destinations=[],
            watched_regions=[],
            notifications_enabled=False,
            ai_provider="none",
            ai_model=None,
            serpapi_key=None,
        )
        summary = _build_settings_summary(settings)
        assert "not configured" in summary
        assert "none configured" in summary


class TestGenerateDigest:
    @pytest.mark.asyncio
    async def test_successful_digest(self):
        deals = [make_deal(), make_deal(id=2, parsed_origin="SYD", parsed_destination="LAX")]
        mock_response = json.dumps({
            "summary": "Two great deals today: AKL-NRT at $499 and SYD-LAX at $499.",
            "highlights": ["AKL-NRT 35% below market", "SYD-LAX deal available"],
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 200,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = await generate_digest(deals)

        assert "AKL-NRT" in result["summary"]
        assert len(result["highlights"]) == 2
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_malformed_response_fallback(self):
        deals = [make_deal()]
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value="Great deals available today!")
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 200,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = await generate_digest(deals)

        assert result["summary"] == "Great deals available today!"
        assert result["highlights"] == []
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_prompt_includes_deal_details(self):
        deals = [make_deal(parsed_origin="MEL", parsed_destination="HKG", parsed_price=899)]
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps({"summary": "Test summary", "highlights": []})

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = capture_prompt
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 200,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            await generate_digest(deals)

        assert "MEL -> HKG" in captured_prompt
        assert "899" in captured_prompt


class TestExplainDeal:
    @pytest.mark.asyncio
    async def test_successful_explanation(self):
        deal = make_deal()
        mock_response = json.dumps({
            "explanation": "This AKL-NRT deal at $499 is 35% below the typical market rate of $770. Air New Zealand offers competitive pricing on this route.",
            "verdict": "great_deal",
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 300,
                "cost_est_usd": 0.001,
            }
            result = await explain_deal(deal)

        assert "35%" in result["explanation"]
        assert result["verdict"] == "great_deal"
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_malformed_response_fallback(self):
        deal = make_deal()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value="This looks like a reasonable deal.")
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 300,
                "cost_est_usd": 0.001,
            }
            result = await explain_deal(deal)

        assert "reasonable deal" in result["explanation"]
        assert result["verdict"] == "not_sure"

    @pytest.mark.asyncio
    async def test_prompt_includes_deal_info(self):
        deal = make_deal(parsed_origin="SYD", parsed_destination="LAX", parsed_price=1200, parsed_currency="AUD")
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps({"explanation": "Test", "verdict": "decent"})

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = capture_prompt
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 300,
                "cost_est_usd": 0.001,
            }
            await explain_deal(deal)

        assert "SYD" in captured_prompt
        assert "LAX" in captured_prompt
        assert "1200" in captured_prompt
        assert "AUD" in captured_prompt


class TestReviewSettings:
    @pytest.mark.asyncio
    async def test_successful_review(self):
        settings = make_settings()
        mock_response = json.dumps({
            "assessment": "Your setup is well-configured with good coverage of NZ and Asian destinations.",
            "suggestions": [
                {"title": "Add more data sources", "description": "Consider adding Skyscanner API for better price data."},
                {"title": "Enable daily digest", "description": "A daily digest can reduce notification fatigue."},
            ],
            "score": 7,
        })

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value=mock_response)
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 150,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            result = await review_settings(settings)

        assert "well-configured" in result["assessment"]
        assert len(result["suggestions"]) == 2
        assert result["score"] == 7
        assert "estimate" in result

    @pytest.mark.asyncio
    async def test_malformed_response_fallback(self):
        settings = make_settings()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = AsyncMock(return_value="Your configuration looks decent.")
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 150,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            result = await review_settings(settings)

        assert "decent" in result["assessment"]
        assert result["suggestions"] == []
        assert result["score"] == 5

    @pytest.mark.asyncio
    async def test_prompt_includes_settings(self):
        settings = make_settings(home_airports=["WLG", "AKL"], watched_destinations=["SFO", "JFK"])
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps({"assessment": "Test", "suggestions": [], "score": 5})

        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.complete = capture_prompt
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 150,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            await review_settings(settings)

        assert "WLG" in captured_prompt
        assert "AKL" in captured_prompt
        assert "SFO" in captured_prompt
        assert "JFK" in captured_prompt


class TestEstimateFunctions:
    def test_estimate_digest(self):
        deals = [make_deal(), make_deal(id=2)]
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 200,
                "output_tokens_est": 300,
                "cost_est_usd": 0.002,
            }
            result = estimate_digest(deals)

        assert "input_tokens_est" in result
        assert "output_tokens_est" in result
        assert "cost_est_usd" in result

    def test_estimate_explain(self):
        deal = make_deal()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 100,
                "output_tokens_est": 300,
                "cost_est_usd": 0.001,
            }
            result = estimate_explain(deal)

        assert "input_tokens_est" in result
        assert "output_tokens_est" in result
        assert "cost_est_usd" in result

    def test_estimate_settings_review(self):
        settings = make_settings()
        with patch("app.services.ai_service.AIService") as MockAI:
            MockAI.estimate_tokens.return_value = {
                "input_tokens_est": 150,
                "output_tokens_est": 500,
                "cost_est_usd": 0.003,
            }
            result = estimate_settings_review(settings)

        assert "input_tokens_est" in result
        assert "output_tokens_est" in result
        assert "cost_est_usd" in result
