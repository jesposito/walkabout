from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.user_settings import UserSettings
from app.services.destinations import DestinationService


PREMIUM_AIRLINES = {
    "qatar", "singapore", "emirates", "air new zealand", "cathay", "ana", "jal",
    "qantas", "korean", "eva", "turkish", "swiss", "lufthansa"
}

BUDGET_AIRLINES = {
    "ryanair", "easyjet", "spirit", "frontier", "jetstar", "scoot", "airasia",
    "cebu pacific", "tiger", "vietjet"
}


class DealScorer:
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = UserSettings.get_or_create(db)
    
    def score_deal(self, deal: Deal) -> float:
        """Score 0-100: relevance(40) + value(30) + recency(20) + quality(10)"""
        score = 0.0
        score += self._score_relevance(deal)
        score += self._score_value(deal)
        score += self._score_recency(deal)
        score += self._score_quality(deal)
        return min(100.0, max(0.0, score))
    
    def _score_relevance(self, deal: Deal) -> float:
        if not deal.is_relevant:
            return 0.0
        
        reason = deal.relevance_reason or ""
        origin = (deal.parsed_origin or "").upper()
        dest = (deal.parsed_destination or "").upper()
        watched = [w.upper() for w in (self.settings.watched_destinations or [])]
        
        if origin == self.settings.home_airport:
            return 40.0
        if dest in watched:
            return 35.0
        if "Similar to" in reason:
            return 25.0
        if "Oceania" in reason or "Asia" in reason:
            return 15.0
        return 10.0
    
    def _score_value(self, deal: Deal) -> float:
        if not deal.parsed_price:
            return 10.0
        
        price = deal.parsed_price
        cabin = (deal.parsed_cabin_class or "ECONOMY").upper()
        
        if cabin == "ECONOMY":
            if price < 200:
                return 30.0
            elif price < 400:
                return 25.0
            elif price < 600:
                return 20.0
            elif price < 1000:
                return 15.0
            return 10.0
        
        elif cabin == "BUSINESS":
            if price < 1500:
                return 30.0
            elif price < 2500:
                return 25.0
            elif price < 4000:
                return 20.0
            return 15.0
        
        elif cabin == "FIRST":
            if price < 3000:
                return 30.0
            elif price < 5000:
                return 25.0
            return 20.0
        
        return 15.0
    
    def _score_recency(self, deal: Deal) -> float:
        if not deal.published_at:
            return 10.0
        
        age = datetime.utcnow() - deal.published_at
        
        if age < timedelta(hours=6):
            return 20.0
        elif age < timedelta(days=1):
            return 18.0
        elif age < timedelta(days=2):
            return 15.0
        elif age < timedelta(days=3):
            return 12.0
        elif age < timedelta(days=7):
            return 8.0
        return 5.0
    
    def _score_quality(self, deal: Deal) -> float:
        score = 5.0
        airline = (deal.parsed_airline or "").lower()
        
        for premium in PREMIUM_AIRLINES:
            if premium in airline:
                score += 3.0
                break
        
        for budget in BUDGET_AIRLINES:
            if budget in airline:
                score -= 2.0
                break
        
        if deal.parsed_cabin_class in ("BUSINESS", "FIRST"):
            score += 2.0
        
        return max(0.0, min(10.0, score))
    
    def update_deal_score(self, deal: Deal) -> Deal:
        deal.score = self.score_deal(deal)
        return deal
    
    def update_all_scores(self) -> int:
        deals = self.db.query(Deal).all()
        for deal in deals:
            self.update_deal_score(deal)
        self.db.commit()
        return len(deals)
    
    def get_top_deals(self, limit: int = 20, relevant_only: bool = True) -> list[Deal]:
        query = self.db.query(Deal)
        if relevant_only:
            query = query.filter(Deal.is_relevant == True)
        return query.order_by(Deal.score.desc()).limit(limit).all()
