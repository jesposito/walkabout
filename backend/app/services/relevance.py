from typing import Optional
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.user_settings import UserSettings
from app.services.destinations import DestinationService, get_alternative_message


OCEANIA_AIRPORTS = {
    'AKL', 'WLG', 'CHC', 'ZQN', 'ROT', 'NPE', 'NSN', 'DUD', 'PMR', 'NPL',
    'SYD', 'MEL', 'BNE', 'PER', 'ADL', 'CBR', 'OOL', 'CNS', 'HBA',
    'NAN', 'SUV', 'APW', 'PPT', 'RAR', 'TBU', 'VLI', 'NOU',
}

OCEANIA_KEYWORDS = [
    'auckland', 'wellington', 'christchurch', 'queenstown', 'new zealand', 'nz',
    'sydney', 'melbourne', 'brisbane', 'perth', 'australia',
    'fiji', 'tahiti', 'rarotonga', 'samoa', 'tonga', 'vanuatu', 'new caledonia',
]

ASIA_AIRPORTS = {
    'TYO', 'NRT', 'HND', 'KIX', 'HKG', 'SIN', 'BKK', 'KUL', 'MNL',
    'ICN', 'TPE', 'PVG', 'PEK', 'CAN', 'SGN', 'HAN', 'DPS',
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
        title_lower = deal.raw_title.lower()
        origin = (deal.parsed_origin or '').upper()
        dest = (deal.parsed_destination or '').upper()
        
        home_airports = self._get_home_airports()
        
        if origin in home_airports:
            return (True, f"Departs from {origin}")
        
        if origin in OCEANIA_AIRPORTS:
            return (True, f"Departs from Oceania ({origin})")
        
        if dest in home_airports:
            return (True, f"Arrives at {dest}")
        
        watched = self.settings.watched_destinations or []
        watched_upper = [w.upper() for w in watched]
        if dest in watched_upper:
            return (True, f"Watched destination ({dest})")
        
        similar_match = DestinationService.is_similar_destination(dest, watched_upper)
        if similar_match:
            watched_dest, group_name, deal_dest = similar_match
            return (True, f"Similar to {watched_dest} ({group_name})")
        
        for keyword in OCEANIA_KEYWORDS:
            if keyword in title_lower:
                return (True, f"Mentions {keyword}")
        
        if dest in OCEANIA_AIRPORTS:
            return (True, f"Destination in Oceania ({dest})")
        
        if dest in ASIA_AIRPORTS:
            return (True, f"Destination in Asia ({dest})")
        
        return (False, None)
    
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
