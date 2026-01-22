"""Template helper functions for Jinja2 templates."""

from app.services.airports import AIRPORTS


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
