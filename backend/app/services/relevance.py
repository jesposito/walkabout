import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.deal import Deal
from app.models.user_settings import UserSettings
from app.services.airports import AIRPORTS, AirportService

logger = logging.getLogger(__name__)

# Proximity radius for "nearby" tier (km)
NEARBY_RADIUS_KM = 500

MAJOR_HUBS = {
    # North America
    'ATL': 'Atlanta', 'DFW': 'Dallas', 'DEN': 'Denver',
    'ORD': 'Chicago', 'LAX': 'Los Angeles', 'JFK': 'New York',
    'EWR': 'Newark', 'SFO': 'San Francisco', 'SEA': 'Seattle',
    'MIA': 'Miami', 'IAH': 'Houston', 'PHX': 'Phoenix',
    'MSP': 'Minneapolis', 'DTW': 'Detroit', 'BOS': 'Boston',
    'IAD': 'Washington Dulles', 'CLT': 'Charlotte', 'MCO': 'Orlando',
    'YYZ': 'Toronto', 'YVR': 'Vancouver',
    # Asia
    'SIN': 'Singapore', 'HKG': 'Hong Kong', 'NRT': 'Tokyo Narita',
    'HND': 'Tokyo Haneda', 'BKK': 'Bangkok', 'KUL': 'Kuala Lumpur',
    'ICN': 'Seoul', 'DOH': 'Doha', 'DXB': 'Dubai',
    # Europe
    'LHR': 'London', 'FRA': 'Frankfurt', 'AMS': 'Amsterdam',
    'CDG': 'Paris', 'MAD': 'Madrid', 'FCO': 'Rome',
    # Oceania
    'SYD': 'Sydney', 'MEL': 'Melbourne', 'AKL': 'Auckland',
}


class RelevanceService:

    def __init__(self, db: Session):
        self.db = db
        self.settings = UserSettings.get_or_create(db)
        self._nearby_cache: Optional[set[str]] = None
        self._domestic_cache: Optional[set[str]] = None

    def _get_home_airports(self) -> set[str]:
        airports = self.settings.home_airports or []
        if not airports and self.settings.home_airport:
            airports = [self.settings.home_airport]
        return {a.upper() for a in airports}

    def _get_nearby_airports(self) -> set[str]:
        """Get airports within NEARBY_RADIUS_KM of any home airport."""
        if self._nearby_cache is not None:
            return self._nearby_cache
        home = self._get_home_airports()
        nearby = set()
        for code in home:
            for apt, dist in AirportService.get_nearby_airports(code, NEARBY_RADIUS_KM):
                nearby.add(apt.code)
        self._nearby_cache = nearby - home  # exclude home airports themselves
        return self._nearby_cache

    def _get_domestic_airports(self) -> set[str]:
        """Get all airports in the same country as any home airport."""
        if self._domestic_cache is not None:
            return self._domestic_cache
        home = self._get_home_airports()
        countries = set()
        for code in home:
            country = AirportService.get_country_for_airport(code)
            if country:
                countries.add(country)
        domestic = set()
        for country in countries:
            for apt in AirportService.get_by_country(country):
                domestic.add(apt.code)
        self._domestic_cache = domestic - home
        return self._domestic_cache

    def score_deal(self, deal: Deal) -> tuple[bool, Optional[str], Optional[str]]:
        """Score a deal's relevance. Returns (is_relevant, reason, category).
        Categories: 'local', 'nearby', 'domestic', 'hub', None."""
        origin = (deal.parsed_origin or '').upper()

        if not origin:
            return (False, None, None)

        home_airports = self._get_home_airports()
        if not home_airports:
            # No home airport set — only hub deals are relevant
            if origin in MAJOR_HUBS:
                return (True, f"Hub: {MAJOR_HUBS[origin]}", "hub")
            return (False, None, None)

        # Tier 1: Local — deal origin IS a home airport
        if origin in home_airports:
            apt = AIRPORTS.get(origin)
            city = apt.city if apt else origin
            return (True, f"From {city} ({origin})", "local")

        # Tier 2: Nearby — within ~500km of a home airport
        nearby = self._get_nearby_airports()
        if origin in nearby:
            apt = AIRPORTS.get(origin)
            city = apt.city if apt else origin
            return (True, f"Nearby: {city} ({origin})", "nearby")

        # Tier 3: Domestic — same country as home airport
        domestic = self._get_domestic_airports()
        if origin in domestic:
            apt = AIRPORTS.get(origin)
            city = apt.city if apt else origin
            return (True, f"Domestic: {city} ({origin})", "domestic")

        # Tier 4: Major hub
        if origin in MAJOR_HUBS:
            return (True, f"Hub: {MAJOR_HUBS[origin]}", "hub")

        return (False, None, None)

    def is_hub_deal(self, deal: Deal) -> bool:
        origin = (deal.parsed_origin or '').upper()
        return origin in MAJOR_HUBS

    def is_home_deal(self, deal: Deal) -> bool:
        origin = (deal.parsed_origin or '').upper()
        home_airports = self._get_home_airports()
        nearby = self._get_nearby_airports()
        return origin in home_airports or origin in nearby

    def update_deal_relevance(self, deal: Deal) -> Deal:
        is_relevant, reason, category = self.score_deal(deal)
        deal.is_relevant = is_relevant
        deal.relevance_reason = reason
        return deal

    def update_all_deals(self) -> int:
        deals = self.db.query(Deal).all()
        updated = 0
        for deal in deals:
            old_relevant = deal.is_relevant
            self.update_deal_relevance(deal)
            if deal.is_relevant != old_relevant:
                updated += 1
        self.db.commit()
        return updated

    def get_relevant_deals(self, limit: int = 50) -> list[Deal]:
        return self.db.query(Deal).filter(
            Deal.is_relevant == True
        ).order_by(Deal.published_at.desc()).limit(limit).all()

    def get_local_deals(self, limit: int = 50) -> list[Deal]:
        home_airports = list(self._get_home_airports())
        if not home_airports:
            return []
        return self.db.query(Deal).filter(
            Deal.parsed_origin.in_(home_airports)
        ).order_by(Deal.published_at.desc()).limit(limit).all()

    def get_regional_deals(self, limit: int = 50) -> list[Deal]:
        """Get deals from nearby + domestic airports."""
        home = self._get_home_airports()
        nearby = self._get_nearby_airports()
        domestic = self._get_domestic_airports()
        regional = list(home | nearby | domestic)
        if not regional:
            return []
        return self.db.query(Deal).filter(
            Deal.parsed_origin.in_(regional)
        ).order_by(Deal.published_at.desc()).limit(limit).all()

    def get_home_deals(self, limit: int = 50) -> list[Deal]:
        return self.get_local_deals(limit)

    def get_hub_deals(self, limit: int = 50) -> list[Deal]:
        hub_codes = list(MAJOR_HUBS.keys())
        return self.db.query(Deal).filter(
            Deal.parsed_origin.in_(hub_codes)
        ).order_by(Deal.published_at.desc()).limit(limit).all()

    def get_hub_counts(self) -> dict[str, int]:
        hub_codes = list(MAJOR_HUBS.keys())
        results = self.db.query(
            Deal.parsed_origin,
            func.count(Deal.id)
        ).filter(
            Deal.parsed_origin.in_(hub_codes)
        ).group_by(Deal.parsed_origin).all()

        return {row[0]: row[1] for row in results}
