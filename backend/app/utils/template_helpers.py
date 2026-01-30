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
    cabin_class: str = "economy",
    currency: str = "NZD"
) -> str:
    cabin_map = {"economy": "1", "premium_economy": "2", "business": "3", "first": "4"}
    cabin_code = cabin_map.get(cabin_class.lower(), "1")
    
    dep_str = departure_date.strftime("%Y-%m-%d")
    base = "https://www.google.com/travel/flights"
    
    query_parts = [f"q=Flights from {origin} to {destination} on {dep_str}"]
    
    if return_date:
        query_parts[0] += f" returning {return_date.strftime('%Y-%m-%d')}"
    
    query_parts.extend([f"curr={currency}", "hl=en"])
    
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
