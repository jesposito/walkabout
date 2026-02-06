"""AI-powered deal intelligence features.

Provides deal digest summaries, deal explanations, and settings optimization
using the configured AI provider.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _parse_json_response(response: str) -> dict:
    """Extract JSON from an AI response, handling markdown code fences."""
    text = response.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    return json.loads(text)


def _build_deals_summary(deals) -> str:
    """Build a human-readable summary of deals for AI prompts."""
    parts = []
    for i, deal in enumerate(deals, 1):
        line = f"{i}. "
        if deal.parsed_origin and deal.parsed_destination:
            line += f"{deal.parsed_origin} -> {deal.parsed_destination}"
        else:
            line += deal.raw_title[:80]

        if deal.parsed_price and deal.parsed_currency:
            line += f" | {deal.parsed_currency} {deal.parsed_price}"

        if deal.parsed_airline:
            line += f" | {deal.parsed_airline}"

        if deal.parsed_cabin_class:
            line += f" | {deal.parsed_cabin_class}"

        if deal.deal_rating is not None:
            line += f" | {deal.deal_rating:.0f}% below market"

        if deal.rating_label:
            line += f" ({deal.rating_label})"

        parts.append(line)

    return "\n".join(parts)


def _build_deal_detail(deal) -> str:
    """Build a detailed summary of a single deal for AI prompts."""
    parts = []
    parts.append(f"Title: {deal.raw_title}")

    if deal.parsed_origin:
        parts.append(f"Origin: {deal.parsed_origin}")
    if deal.parsed_destination:
        parts.append(f"Destination: {deal.parsed_destination}")
    if deal.parsed_price and deal.parsed_currency:
        parts.append(f"Price: {deal.parsed_currency} {deal.parsed_price}")
    if deal.parsed_airline:
        parts.append(f"Airline: {deal.parsed_airline}")
    if deal.parsed_cabin_class:
        parts.append(f"Cabin class: {deal.parsed_cabin_class}")
    if deal.deal_rating is not None:
        parts.append(f"Discount vs market: {deal.deal_rating:.0f}%")
    if deal.rating_label:
        parts.append(f"Rating: {deal.rating_label}")
    if deal.market_price and deal.market_currency:
        parts.append(f"Market price: {deal.market_currency} {deal.market_price:.0f}")
    if deal.source:
        source_val = deal.source.value if hasattr(deal.source, 'value') else str(deal.source)
        parts.append(f"Source: {source_val}")
    if deal.published_at:
        parts.append(f"Published: {deal.published_at.strftime('%Y-%m-%d %H:%M') if hasattr(deal.published_at, 'strftime') else str(deal.published_at)}")

    return "\n".join(parts)


def _build_settings_summary(settings) -> str:
    """Build a human-readable summary of user settings for AI review."""
    parts = []

    home_airports = settings.home_airports or []
    if home_airports:
        parts.append(f"Home airports: {', '.join(home_airports)}")
    elif settings.home_airport:
        parts.append(f"Home airport: {settings.home_airport}")
    else:
        parts.append("Home airport: not configured")

    parts.append(f"Home region: {settings.home_region or 'not set'}")

    watched = settings.watched_destinations or []
    if watched:
        parts.append(f"Dream destinations: {', '.join(watched)}")
    else:
        parts.append("Dream destinations: none configured")

    watched_regions = settings.watched_regions or []
    if watched_regions:
        parts.append(f"Watched regions: {', '.join(watched_regions)}")

    parts.append(f"Preferred currency: {settings.preferred_currency or 'NZD'}")

    # Notification settings
    parts.append(f"Notifications: {'enabled' if settings.notifications_enabled else 'disabled'}")
    if settings.notifications_enabled:
        parts.append(f"Notification provider: {settings.notification_provider or 'none'}")
        parts.append(f"Deal cooldown: {settings.deal_cooldown_minutes or 60} minutes")
        parts.append(f"Daily digest: {'enabled' if settings.daily_digest_enabled else 'disabled'}")

    # AI settings
    ai_provider = settings.ai_provider or "none"
    parts.append(f"AI provider: {ai_provider}")
    if settings.ai_model:
        parts.append(f"AI model: {settings.ai_model}")

    # API keys (presence only, not values)
    api_keys = []
    if settings.seats_aero_api_key:
        api_keys.append("Seats.aero")
    if settings.serpapi_key:
        api_keys.append("SerpAPI")
    if settings.skyscanner_api_key:
        api_keys.append("Skyscanner")
    if settings.amadeus_client_id:
        api_keys.append("Amadeus")
    if api_keys:
        parts.append(f"Data source APIs configured: {', '.join(api_keys)}")
    else:
        parts.append("Data source APIs: none configured")

    return "\n".join(parts)


DEAL_DIGEST_SYSTEM = """You are a flight deal analyst. Given a list of recent flight deals,
generate a concise morning briefing summary in 2-3 sentences.

Rules:
- Highlight the best deals (biggest discounts, most popular routes)
- Mention any notable trends (e.g., many deals to a region, specific airlines)
- Keep it conversational and helpful
- If deals have ratings, mention the standout ones
- Do NOT use emoji

Return ONLY valid JSON:
{"summary": "Your 2-3 sentence briefing here.", "highlights": ["Key highlight 1", "Key highlight 2"]}"""


DEAL_EXPLAIN_SYSTEM = """You are a flight deal analyst. Given details about a specific flight deal,
explain why this is (or isn't) a good deal based on the available data.

Consider:
- How the price compares to the market price (if available)
- The route and typical pricing for it
- The cabin class and whether the price is unusual
- Seasonal factors
- The airline and its reputation on this route

Rules:
- Be specific about WHY this is a deal, not just that it is one
- If market data is available, reference the discount percentage
- Keep the explanation to 2-4 sentences
- Be honest if there isn't enough data to fully assess
- Do NOT use emoji

Return ONLY valid JSON:
{"explanation": "Your 2-4 sentence explanation here.", "verdict": "great_deal|good_deal|decent|not_sure|overpriced"}"""


SETTINGS_REVIEW_SYSTEM = """You are a flight deal monitoring configuration advisor. Given a user's
settings, suggest improvements to help them find better deals.

Consider:
- Whether their home airports and destinations are well-configured
- Whether notification settings are optimal (not too noisy, not too quiet)
- Whether they're using available data sources
- Whether their AI and monitoring configuration is well-tuned
- General best practices for deal hunting

Rules:
- Provide 2-5 specific, actionable suggestions
- Explain WHY each suggestion would help
- Be encouraging about what's already well-configured
- Do NOT suggest specific API keys or credentials
- Do NOT use emoji

Return ONLY valid JSON:
{"assessment": "1-2 sentence overall assessment.", "suggestions": [{"title": "Suggestion title", "description": "Why and how this helps"}], "score": 1-10}"""


async def generate_digest(deals, db=None) -> dict:
    """Generate an AI-powered digest summary of recent deals.

    Args:
        deals: List of Deal model instances.
        db: Optional database session for usage logging.

    Returns:
        Dict with "summary", "highlights", and "estimate" keys.
    """
    from app.services.ai_service import AIService

    deals_summary = _build_deals_summary(deals)
    prompt = f"Summarize these recent flight deals into a morning briefing:\n\n{deals_summary}"

    estimate = AIService.estimate_tokens(prompt, DEAL_DIGEST_SYSTEM, max_tokens=300)

    response = await AIService.complete(
        prompt=prompt,
        system_prompt=DEAL_DIGEST_SYSTEM,
        max_tokens=300,
        db=db,
        endpoint="deal_digest",
    )

    try:
        result = _parse_json_response(response)
        return {
            "summary": result.get("summary", "No summary available."),
            "highlights": result.get("highlights", []),
            "estimate": estimate,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse deal digest response: {e}")
        return {
            "summary": response.strip()[:300],
            "highlights": [],
            "estimate": estimate,
        }


async def explain_deal(deal, db=None) -> dict:
    """Generate an AI explanation of why a deal is notable.

    Args:
        deal: A Deal model instance.
        db: Optional database session for usage logging.

    Returns:
        Dict with "explanation", "verdict", and "estimate" keys.
    """
    from app.services.ai_service import AIService

    deal_detail = _build_deal_detail(deal)
    prompt = f"Explain why this flight deal is notable:\n\n{deal_detail}"

    estimate = AIService.estimate_tokens(prompt, DEAL_EXPLAIN_SYSTEM, max_tokens=300)

    response = await AIService.complete(
        prompt=prompt,
        system_prompt=DEAL_EXPLAIN_SYSTEM,
        max_tokens=300,
        db=db,
        endpoint="deal_explain",
    )

    try:
        result = _parse_json_response(response)
        return {
            "explanation": result.get("explanation", "Unable to assess this deal."),
            "verdict": result.get("verdict", "not_sure"),
            "estimate": estimate,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse deal explanation response: {e}")
        return {
            "explanation": response.strip()[:300],
            "verdict": "not_sure",
            "estimate": estimate,
        }


async def review_settings(settings, db=None) -> dict:
    """AI-powered review and optimization of user settings.

    Args:
        settings: A UserSettings model instance.
        db: Optional database session for usage logging.

    Returns:
        Dict with "assessment", "suggestions", "score", and "estimate" keys.
    """
    from app.services.ai_service import AIService

    settings_summary = _build_settings_summary(settings)
    prompt = f"Review this flight deal monitoring configuration and suggest improvements:\n\n{settings_summary}"

    estimate = AIService.estimate_tokens(prompt, SETTINGS_REVIEW_SYSTEM, max_tokens=500)

    response = await AIService.complete(
        prompt=prompt,
        system_prompt=SETTINGS_REVIEW_SYSTEM,
        max_tokens=500,
        db=db,
        endpoint="settings_review",
    )

    try:
        result = _parse_json_response(response)
        return {
            "assessment": result.get("assessment", "Unable to assess configuration."),
            "suggestions": result.get("suggestions", []),
            "score": result.get("score", 5),
            "estimate": estimate,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse settings review response: {e}")
        return {
            "assessment": response.strip()[:300],
            "suggestions": [],
            "score": 5,
            "estimate": estimate,
        }


def estimate_digest(deals) -> dict:
    """Return a token/cost estimate for a deal digest without running the AI."""
    from app.services.ai_service import AIService

    deals_summary = _build_deals_summary(deals)
    prompt = f"Summarize these recent flight deals into a morning briefing:\n\n{deals_summary}"
    return AIService.estimate_tokens(prompt, DEAL_DIGEST_SYSTEM, max_tokens=300)


def estimate_explain(deal) -> dict:
    """Return a token/cost estimate for a deal explanation without running the AI."""
    from app.services.ai_service import AIService

    deal_detail = _build_deal_detail(deal)
    prompt = f"Explain why this flight deal is notable:\n\n{deal_detail}"
    return AIService.estimate_tokens(prompt, DEAL_EXPLAIN_SYSTEM, max_tokens=300)


def estimate_settings_review(settings) -> dict:
    """Return a token/cost estimate for a settings review without running the AI."""
    from app.services.ai_service import AIService

    settings_summary = _build_settings_summary(settings)
    prompt = f"Review this flight deal monitoring configuration and suggest improvements:\n\n{settings_summary}"
    return AIService.estimate_tokens(prompt, SETTINGS_REVIEW_SYSTEM, max_tokens=500)
