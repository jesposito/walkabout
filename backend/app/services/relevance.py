from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.deal import Deal
from app.models.user_settings import UserSettings

NZ_AIRPORTS = {'AKL', 'WLG', 'CHC', 'ZQN', 'ROT', 'NPE', 'NSN', 'DUD', 'PMR', 'NPL', 'TRG', 'HLZ'}
AU_AIRPORTS = {'SYD', 'MEL', 'BNE', 'PER', 'ADL', 'CBR', 'OOL', 'CNS', 'HBA', 'DRW', 'TSV', 'CAI'}
PACIFIC_AIRPORTS = {'NAN', 'SUV', 'APW', 'PPT', 'RAR', 'TBU', 'VLI', 'NOU', 'HNL', 'OGG', 'LIH'}

REGION_MAP = {
    'NZ': NZ_AIRPORTS,
    'AU': AU_AIRPORTS,
    'PACIFIC': PACIFIC_AIRPORTS,
}

def get_region_for_airport(code: str) -> Optional[str]:
    code = code.upper()
    for region, airports in REGION_MAP.items():
        if code in airports:
            return region
    return None

def get_home_region_airports(home_airports: set[str]) -> set[str]:
    regions = set()
    for airport in home_airports:
        region = get_region_for_airport(airport)
        if region:
            regions.add(region)
    
    result = set()
    for region in regions:
        result.update(REGION_MAP.get(region, set()))
    return result


ALL_REGIONAL_AIRPORTS = NZ_AIRPORTS | AU_AIRPORTS | PACIFIC_AIRPORTS

MAJOR_HUBS = {
    'LAX': 'Los Angeles',
    'SFO': 'San Francisco',
    'SEA': 'Seattle',
    'JFK': 'New York',
    'ORD': 'Chicago',
    'SIN': 'Singapore',
    'HKG': 'Hong Kong',
    'NRT': 'Tokyo Narita',
    'HND': 'Tokyo Haneda',
    'BKK': 'Bangkok',
    'KUL': 'Kuala Lumpur',
    'DOH': 'Doha',
    'DXB': 'Dubai',
    'LHR': 'London',
    'FRA': 'Frankfurt',
    'AMS': 'Amsterdam',
    'CDG': 'Paris',
}


class RelevanceService:
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = UserSettings.get_or_create(db)
    
    def _get_home_airports(self) -> set[str]:
        airports = self.settings.home_airports or []
        if not airports and self.settings.home_airport:
            airports = [self.settings.home_airport]
        return {a.upper() for a in airports}
    
    def score_deal(self, deal: Deal) -> tuple[bool, Optional[str]]:
        origin = (deal.parsed_origin or '').upper()
        
        if not origin:
            return (False, None)
        
        home_airports = self._get_home_airports()
        home_region_airports = get_home_region_airports(home_airports)
        
        if origin in home_airports:
            return (True, f"From {origin}")
        
        if origin in home_region_airports:
            return (True, f"From {origin}")
        
        if origin in MAJOR_HUBS:
            return (True, f"Hub: {MAJOR_HUBS[origin]}")
        
        return (False, None)
    
    def is_hub_deal(self, deal: Deal) -> bool:
        origin = (deal.parsed_origin or '').upper()
        return origin in MAJOR_HUBS
    
    def is_home_deal(self, deal: Deal) -> bool:
        origin = (deal.parsed_origin or '').upper()
        home_airports = self._get_home_airports()
        home_region_airports = get_home_region_airports(home_airports)
        return origin in home_airports or origin in home_region_airports
    
    def update_deal_relevance(self, deal: Deal) -> Deal:
        is_relevant, reason = self.score_deal(deal)
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
        regional_airports = list(ALL_REGIONAL_AIRPORTS)
        return self.db.query(Deal).filter(
            Deal.parsed_origin.in_(regional_airports)
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
