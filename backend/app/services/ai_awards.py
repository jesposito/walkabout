"""AI-powered award flight intelligence features.

Provides award pattern analysis (sweet spot finding) and mile valuation
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


def _build_observation_summary(search, observations) -> str:
    """Build a human-readable summary of an award search and its observation history."""
    parts = []

    parts.append(f"Route: {search.origin} -> {search.destination}")
    parts.append(f"Cabin class: {search.cabin_class}")

    if search.program:
        parts.append(f"Program: {search.program}")
    else:
        parts.append("Program: all programs")

    if search.date_start or search.date_end:
        date_range = ""
        if search.date_start:
            date_range += search.date_start.strftime("%Y-%m-%d")
        else:
            date_range += "any start"
        date_range += " to "
        if search.date_end:
            date_range += search.date_end.strftime("%Y-%m-%d")
        else:
            date_range += "any end"
        parts.append(f"Date range: {date_range}")

    if search.min_seats > 1:
        parts.append(f"Minimum seats needed: {search.min_seats}")

    if search.direct_only:
        parts.append("Direct flights only: yes")

    if observations:
        parts.append(f"\nObservation history ({len(observations)} data points):")
        for obs in observations:
            obs_parts = []
            obs_parts.append(f"  Date: {obs.observed_at.strftime('%Y-%m-%d %H:%M')}")
            obs_parts.append(f"    Total options: {obs.total_options}")
            if obs.programs_with_availability:
                obs_parts.append(f"    Programs available: {', '.join(obs.programs_with_availability)}")
            if obs.best_economy_miles:
                obs_parts.append(f"    Best economy: {obs.best_economy_miles:,} miles")
            if obs.best_business_miles:
                obs_parts.append(f"    Best business: {obs.best_business_miles:,} miles")
            if obs.best_first_miles:
                obs_parts.append(f"    Best first: {obs.best_first_miles:,} miles")
            if obs.max_seats_available:
                obs_parts.append(f"    Max seats: {obs.max_seats_available}")
            obs_parts.append(f"    Changed from previous: {'yes' if obs.is_changed else 'no'}")
            parts.append("\n".join(obs_parts))
    else:
        parts.append("\nNo observation history available yet.")

    return "\n".join(parts)


def _build_mile_value_context(
    origin: str,
    destination: str,
    miles: int,
    program: str,
    cabin: str,
    cash_price: Optional[float] = None,
) -> str:
    """Build context string for mile valuation analysis."""
    parts = []
    parts.append(f"Route: {origin} -> {destination}")
    parts.append(f"Program: {program}")
    parts.append(f"Cabin class: {cabin}")
    parts.append(f"Miles required: {miles:,}")

    if cash_price is not None:
        parts.append(f"Cash price for equivalent ticket: ${cash_price:,.2f} USD")
        cpp = (cash_price / miles) * 100 if miles > 0 else 0
        parts.append(f"Raw cents-per-mile: {cpp:.2f} cpp")
    else:
        parts.append("Cash price: not provided (estimate based on typical fares)")

    return "\n".join(parts)


AWARD_PATTERNS_SYSTEM = """You are an award flight availability analyst. Given a tracked award search
and its observation history, identify patterns and sweet spots in award availability.

Analyze:
- Which programs consistently offer the best rates
- Days or periods with better availability
- Trends in availability (improving, declining, stable)
- Whether the miles required are competitive for this route and cabin
- Actionable recommendations for when and how to book

Return ONLY valid JSON:
{
  "sweet_spots": [
    {"program": "program_name", "insight": "1-2 sentence finding"}
  ],
  "timing": "1-2 sentences about best timing to book",
  "trend": "improving|declining|stable|insufficient_data",
  "recommendation": "2-3 sentence actionable recommendation",
  "best_value_program": "program_name or null if insufficient data"
}"""


MILE_VALUE_SYSTEM = """You are a miles and points valuation expert. Given a redemption opportunity,
evaluate whether it represents good value for the miles spent.

Consider:
- Industry standard valuations for the loyalty program
- Typical cash fares for this route and cabin class
- Whether this represents above-average, average, or below-average value
- The opportunity cost of spending miles on this redemption

Return ONLY valid JSON:
{
  "cents_per_mile": 1.5,
  "rating": "excellent|good|fair|poor",
  "reasoning": "2-3 sentence explanation of the valuation",
  "benchmark": "Brief note on typical valuations for this program"
}"""


async def find_patterns(search, observations, db=None) -> dict:
    """Analyze observation history to find award availability patterns.

    Args:
        search: A TrackedAwardSearch model instance.
        observations: List of AwardObservation model instances.
        db: Optional database session for usage logging.

    Returns:
        Dict with "sweet_spots", "timing", "trend", "recommendation",
        "best_value_program", and "estimate" keys.
    """
    from app.services.ai_service import AIService

    summary = _build_observation_summary(search, observations)
    prompt = f"Analyze this award search history and identify patterns:\n\n{summary}"

    estimate = AIService.estimate_tokens(prompt, AWARD_PATTERNS_SYSTEM, max_tokens=500)

    response = await AIService.complete(
        prompt=prompt,
        system_prompt=AWARD_PATTERNS_SYSTEM,
        max_tokens=500,
        db=db,
        endpoint="award_patterns",
    )

    try:
        result = _parse_json_response(response)
        return {
            "sweet_spots": result.get("sweet_spots", []),
            "timing": result.get("timing", ""),
            "trend": result.get("trend", "insufficient_data"),
            "recommendation": result.get("recommendation", ""),
            "best_value_program": result.get("best_value_program"),
            "estimate": estimate,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse award patterns response: {e}")
        return {
            "sweet_spots": [],
            "timing": response.strip()[:200],
            "trend": "insufficient_data",
            "recommendation": "",
            "best_value_program": None,
            "estimate": estimate,
        }


def estimate_patterns(search, observations) -> dict:
    """Return a token/cost estimate for pattern analysis without running the AI."""
    from app.services.ai_service import AIService

    summary = _build_observation_summary(search, observations)
    prompt = f"Analyze this award search history and identify patterns:\n\n{summary}"
    return AIService.estimate_tokens(prompt, AWARD_PATTERNS_SYSTEM, max_tokens=500)


async def evaluate_miles(
    origin: str,
    destination: str,
    miles: int,
    program: str,
    cabin: str,
    cash_price: Optional[float] = None,
    db=None,
) -> dict:
    """Evaluate the value of a miles redemption.

    Args:
        origin: Origin airport IATA code.
        destination: Destination airport IATA code.
        miles: Number of miles required.
        program: Loyalty program name.
        cabin: Cabin class (economy, business, first, etc.).
        cash_price: Optional cash price in USD for comparison.
        db: Optional database session for usage logging.

    Returns:
        Dict with "cents_per_mile", "rating", "reasoning", "benchmark",
        and "estimate" keys.
    """
    from app.services.ai_service import AIService

    context = _build_mile_value_context(origin, destination, miles, program, cabin, cash_price)
    prompt = f"Evaluate this miles redemption:\n\n{context}"

    estimate = AIService.estimate_tokens(prompt, MILE_VALUE_SYSTEM, max_tokens=300)

    response = await AIService.complete(
        prompt=prompt,
        system_prompt=MILE_VALUE_SYSTEM,
        max_tokens=300,
        db=db,
        endpoint="mile_value",
    )

    try:
        result = _parse_json_response(response)
        return {
            "cents_per_mile": result.get("cents_per_mile", 0),
            "rating": result.get("rating", "fair"),
            "reasoning": result.get("reasoning", ""),
            "benchmark": result.get("benchmark", ""),
            "estimate": estimate,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse mile value response: {e}")
        return {
            "cents_per_mile": 0,
            "rating": "fair",
            "reasoning": response.strip()[:200],
            "benchmark": "",
            "estimate": estimate,
        }


def estimate_mile_value(
    origin: str,
    destination: str,
    miles: int,
    program: str,
    cabin: str,
    cash_price: Optional[float] = None,
) -> dict:
    """Return a token/cost estimate for mile valuation without running the AI."""
    from app.services.ai_service import AIService

    context = _build_mile_value_context(origin, destination, miles, program, cabin, cash_price)
    prompt = f"Evaluate this miles redemption:\n\n{context}"
    return AIService.estimate_tokens(prompt, MILE_VALUE_SYSTEM, max_tokens=300)
