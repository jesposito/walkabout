# SQLAlchemy models
from app.models.search_definition import SearchDefinition, TripType, CabinClass, StopsFilter
from app.models.flight_price import FlightPrice
from app.models.scrape_health import ScrapeHealth
from app.models.alert import Alert

# Legacy model - kept for backwards compatibility during migration
from app.models.route import Route

__all__ = [
    # Core models (Oracle Review)
    "SearchDefinition",
    "FlightPrice", 
    "ScrapeHealth",
    "Alert",
    # Enums
    "TripType",
    "CabinClass", 
    "StopsFilter",
    # Legacy
    "Route",
]
