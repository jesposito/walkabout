"""Template helper functions for Jinja2 templates."""

from datetime import date
from typing import Optional
from urllib.parse import quote

from app.services.airports import AIRPORTS


def build_google_flights_url(
    origin: str,
    destination: str,
    departure_date: date,
    return_date: Optional[date] = None,
    adults: int = 1,
    children: int = 0,
    infants_in_seat: int = 0,
    infants_on_lap: int = 0,
    cabin_class: str = "economy",
    stops_filter: str = "any",
    currency: str = "NZD",
    carry_on_bags: int = 0,
    checked_bags: int = 0,
) -> str:
    """
    Build a Google Flights URL with all filter parameters.

    This is the SINGLE source of truth for Google Flights URL construction.
    Used by: Playwright scraper, booking links, trip plan search.

    Filters are passed as natural language hints in the q= parameter since
    Google Flights parses NL queries. This is best-effort for the scraper
    (actual filtering happens server-side by Google).
    """
    dep_str = departure_date.strftime("%Y-%m-%d")
    base = "https://www.google.com/travel/flights"

    # Build natural language query with filter hints
    query = f"Flights from {origin} to {destination} on {dep_str}"

    if return_date:
        query += f" returning {return_date.strftime('%Y-%m-%d')}"

    # Cabin class NL hint
    cabin_lower = cabin_class.lower()
    if cabin_lower in ("business", "first"):
        query += f" {cabin_lower} class"
    elif cabin_lower == "premium_economy":
        query += " premium economy"

    # Stops NL hint
    stops_lower = stops_filter.lower()
    if stops_lower == "nonstop":
        query += " nonstop"
    elif stops_lower == "one_stop":
        query += " 1 stop or fewer"

    # Passenger count hints (only if non-default)
    total_passengers = adults + children + infants_in_seat + infants_on_lap
    if total_passengers > 1:
        parts = []
        if adults > 1:
            parts.append(f"{adults} adults")
        if children > 0:
            parts.append(f"{children} {'child' if children == 1 else 'children'}")
        if infants_in_seat + infants_on_lap > 0:
            infant_total = infants_in_seat + infants_on_lap
            parts.append(f"{infant_total} {'infant' if infant_total == 1 else 'infants'}")
        if parts:
            query += " " + " ".join(parts)

    query_parts = [f"q={quote(query)}"]
    query_parts.extend([f"curr={currency}", "hl=en", "gl=nz"])

    return f"{base}?{'&'.join(query_parts)}"


def get_airport_display(code: str) -> dict:
    """Get airport display info for a code.
    
    Returns dict with code, city, country for use in templates.
    If code not found, returns just the code.
    """
    if not code:
        return {"code": "", "city": "", "country": "", "label": ""}
    
    code = code.upper().strip()
    airport = AIRPORTS.get(code)
    
    if airport:
        return {
            "code": airport.code,
            "city": airport.city,
            "country": airport.country,
            "label": f"{airport.code} ({airport.city})"
        }
    return {
        "code": code,
        "city": "",
        "country": "",
        "label": code
    }


def get_airports_dict() -> dict:
    """Get all airports as a simple dict for JavaScript lookup.
    
    Returns dict mapping code -> {city, country, name}.
    """
    return {
        code: {
            "city": a.city,
            "country": a.country,
            "name": a.name,
            "region": a.region
        }
        for code, a in AIRPORTS.items()
    }
