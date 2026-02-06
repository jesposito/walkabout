"""AI-powered trip intelligence features.

Provides trip naming, feasibility checking, and destination recommendations
using the configured AI provider.
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _build_trip_summary(trip) -> str:
    """Build a human-readable summary of a trip plan for AI prompts."""
    parts = []

    if trip.origins:
        parts.append(f"Origin airports: {', '.join(trip.origins)}")
    else:
        parts.append("Origin airports: not specified")

    if trip.destinations:
        parts.append(f"Destination airports: {', '.join(trip.destinations)}")
    else:
        parts.append("Destination: not specified (open to anywhere)")

    if trip.destination_types:
        parts.append(f"Destination types: {', '.join(trip.destination_types)}")

    if trip.legs:
        leg_strs = []
        for leg in trip.legs:
            leg_str = f"{leg.get('origin', '?')} -> {leg.get('destination', '?')}"
            if leg.get('date_start'):
                leg_str += f" ({leg['date_start']}"
                if leg.get('date_end'):
                    leg_str += f" to {leg['date_end']}"
                leg_str += ")"
            leg_strs.append(leg_str)
        parts.append(f"Multi-city legs: {'; '.join(leg_strs)}")

    if trip.available_from or trip.available_to:
        date_range = ""
        if trip.available_from:
            date_range += trip.available_from.strftime("%Y-%m-%d")
        else:
            date_range += "any start"
        date_range += " to "
        if trip.available_to:
            date_range += trip.available_to.strftime("%Y-%m-%d")
        else:
            date_range += "any end"
        parts.append(f"Travel window: {date_range}")

    parts.append(f"Trip duration: {trip.trip_duration_min}-{trip.trip_duration_max} days")

    if trip.budget_max:
        parts.append(f"Budget: up to {trip.budget_max} {trip.budget_currency} total")
    else:
        parts.append("Budget: not specified")

    parts.append(f"Travelers: {trip.travelers_adults} adult(s), {trip.travelers_children} child(ren)")

    if trip.cabin_classes:
        parts.append(f"Cabin class: {', '.join(trip.cabin_classes)}")

    if trip.notes:
        parts.append(f"Notes: {trip.notes}")

    return "\n".join(parts)


def _parse_json_response(response: str) -> dict:
    """Extract JSON from an AI response, handling markdown code fences."""
    text = response.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    return json.loads(text)


TRIP_NAMER_SYSTEM = """You are a creative travel naming assistant. Given trip plan details,
generate a fun, memorable trip name and a one-line vibe description.

Rules:
- The name should be catchy, 2-5 words max
- The vibe should be one sentence capturing the feel of the trip
- If no destination is set, lean into the mystery/adventure angle
- Consider the budget level, cabin class, and trip style
- Do NOT use emoji in the name or vibe

Return ONLY valid JSON:
{"name": "Trip Name Here", "vibe": "One-line vibe description here."}"""


TRIP_FEASIBILITY_SYSTEM = """You are a travel feasibility analyst. Given trip plan details,
evaluate whether the trip is realistic based on your knowledge of typical airfares,
route availability, seasonal patterns, and travel logistics.

Consider:
- Budget vs typical fares for the route and cabin class
- Whether the route exists or requires connections
- Time of year and seasonal pricing
- Trip duration vs distance
- Number of travelers and total budget impact

Return ONLY valid JSON:
{"verdict": "A 1-2 sentence assessment", "reasoning": "2-4 sentences explaining your analysis", "confidence": "high|medium|low"}"""


DESTINATION_RECOMMENDER_SYSTEM = """You are a destination recommendation engine. Given a traveler's
home airports, travel dates, and budget, suggest 3-5 destinations that would be good fits.

Consider:
- Route availability from the origin airports
- Seasonal conditions at the destination during travel dates
- Budget feasibility for the route
- Variety in suggestions (mix of popular and hidden gems)
- Use real IATA airport codes

Return ONLY valid JSON:
{"suggestions": [{"airport": "XXX", "city": "City Name", "reasoning": "1-2 sentence explanation"}]}"""


async def name_trip(trip, db=None) -> dict:
    """Generate a fun name and vibe description for a trip plan.

    Args:
        trip: A TripPlan model instance.
        db: Optional database session for usage logging.

    Returns:
        Dict with "name", "vibe", and "estimate" keys.
    """
    from app.services.ai_service import AIService

    trip_summary = _build_trip_summary(trip)
    prompt = f"Generate a creative name and vibe for this trip:\n\n{trip_summary}"

    estimate = AIService.estimate_tokens(prompt, TRIP_NAMER_SYSTEM, max_tokens=150)

    response = await AIService.complete(
        prompt=prompt,
        system_prompt=TRIP_NAMER_SYSTEM,
        max_tokens=150,
        db=db,
        endpoint="trip_namer",
    )

    try:
        result = _parse_json_response(response)
        return {
            "name": result.get("name", "Untitled Trip"),
            "vibe": result.get("vibe", ""),
            "estimate": estimate,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse trip name response: {e}")
        return {
            "name": "Untitled Trip",
            "vibe": response.strip()[:200],
            "estimate": estimate,
        }


async def check_feasibility(trip, db=None) -> dict:
    """Evaluate whether a trip plan is realistic.

    Args:
        trip: A TripPlan model instance.
        db: Optional database session for usage logging.

    Returns:
        Dict with "verdict", "reasoning", "confidence", and "estimate" keys.
    """
    from app.services.ai_service import AIService

    trip_summary = _build_trip_summary(trip)
    prompt = f"Evaluate the feasibility of this trip plan:\n\n{trip_summary}"

    estimate = AIService.estimate_tokens(prompt, TRIP_FEASIBILITY_SYSTEM, max_tokens=300)

    response = await AIService.complete(
        prompt=prompt,
        system_prompt=TRIP_FEASIBILITY_SYSTEM,
        max_tokens=300,
        db=db,
        endpoint="trip_feasibility",
    )

    try:
        result = _parse_json_response(response)
        return {
            "verdict": result.get("verdict", "Unable to assess."),
            "reasoning": result.get("reasoning", ""),
            "confidence": result.get("confidence", "low"),
            "estimate": estimate,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse feasibility response: {e}")
        return {
            "verdict": response.strip()[:200],
            "reasoning": "",
            "confidence": "low",
            "estimate": estimate,
        }


async def suggest_destinations(
    origins: list[str],
    dates: dict,
    budget: dict,
    cabin_classes: Optional[list[str]] = None,
    travelers: Optional[dict] = None,
    db=None,
) -> dict:
    """Suggest destinations based on origin airports, dates, and budget.

    Args:
        origins: List of origin IATA airport codes.
        dates: Dict with optional "available_from" and "available_to" date strings.
        budget: Dict with optional "budget_max" (int) and "budget_currency" (str).
        cabin_classes: Optional list of cabin classes.
        travelers: Optional dict with "adults" and "children" counts.
        db: Optional database session for usage logging.

    Returns:
        Dict with "suggestions" list and "estimate" keys.
    """
    from app.services.ai_service import AIService

    parts = []
    parts.append(f"Home airports: {', '.join(origins) if origins else 'not specified'}")

    if dates.get("available_from") or dates.get("available_to"):
        date_str = f"{dates.get('available_from', 'any')} to {dates.get('available_to', 'any')}"
        parts.append(f"Travel dates: {date_str}")

    if dates.get("duration_min") or dates.get("duration_max"):
        parts.append(f"Trip duration: {dates.get('duration_min', 3)}-{dates.get('duration_max', 14)} days")

    if budget.get("budget_max"):
        parts.append(f"Budget: up to {budget['budget_max']} {budget.get('budget_currency', 'NZD')} total")
    else:
        parts.append("Budget: flexible")

    if cabin_classes:
        parts.append(f"Cabin class: {', '.join(cabin_classes)}")

    if travelers:
        parts.append(
            f"Travelers: {travelers.get('adults', 2)} adult(s), "
            f"{travelers.get('children', 0)} child(ren)"
        )

    prompt = f"Suggest destinations for this traveler:\n\n" + "\n".join(parts)

    estimate = AIService.estimate_tokens(prompt, DESTINATION_RECOMMENDER_SYSTEM, max_tokens=500)

    response = await AIService.complete(
        prompt=prompt,
        system_prompt=DESTINATION_RECOMMENDER_SYSTEM,
        max_tokens=500,
        db=db,
        endpoint="trip_destinations",
    )

    try:
        result = _parse_json_response(response)
        suggestions = result.get("suggestions", [])
        return {
            "suggestions": suggestions,
            "estimate": estimate,
        }
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"Failed to parse destination suggestions response: {e}")
        return {
            "suggestions": [],
            "estimate": estimate,
        }


def estimate_name_trip(trip) -> dict:
    """Return a token/cost estimate for naming a trip without running the AI."""
    from app.services.ai_service import AIService

    trip_summary = _build_trip_summary(trip)
    prompt = f"Generate a creative name and vibe for this trip:\n\n{trip_summary}"
    return AIService.estimate_tokens(prompt, TRIP_NAMER_SYSTEM, max_tokens=150)


def estimate_feasibility(trip) -> dict:
    """Return a token/cost estimate for a feasibility check without running the AI."""
    from app.services.ai_service import AIService

    trip_summary = _build_trip_summary(trip)
    prompt = f"Evaluate the feasibility of this trip plan:\n\n{trip_summary}"
    return AIService.estimate_tokens(prompt, TRIP_FEASIBILITY_SYSTEM, max_tokens=300)
