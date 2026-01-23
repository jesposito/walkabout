from typing import Optional
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.user_settings import UserSettings


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
        
        if origin in home_airports:
            return (True, f"From {origin}")
        
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
    
    def get_deals_from_home_airports(self, limit: int = 100) -> list[Deal]:
        home_airports = list(self._get_home_airports())
        if not home_airports:
            return []
        return self.db.query(Deal).filter(
            Deal.parsed_origin.in_(home_airports)
        ).order_by(Deal.published_at.desc()).limit(limit).all()
