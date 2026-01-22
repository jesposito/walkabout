from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.trip_plan import TripPlan
from app.models.deal import Deal
from app.services.destinations import DestinationService
from app.services.destination_types import DestinationTypeService
from app.services.currency import CurrencyService


class TripMatcher:
    
    def __init__(self, db: Session):
        self.db = db
    
    def match_deal_to_plans(self, deal: Deal) -> list[tuple[TripPlan, float]]:
        active_plans = self.db.query(TripPlan).filter(TripPlan.is_active == True).all()
        matches = []
        
        for plan in active_plans:
            score = self._score_match(deal, plan)
            if score > 0:
                matches.append((plan, score))
        
        return sorted(matches, key=lambda x: -x[1])
    
    def _score_match(self, deal: Deal, plan: TripPlan) -> float:
        score = 0.0
        
        deal_origin = (deal.parsed_origin or "").upper()
        deal_dest = (deal.parsed_destination or "").upper()
        deal_title = deal.raw_title or ""
        plan_origins = [o.upper() for o in (plan.origins or [])]
        plan_dests = [d.upper() for d in (plan.destinations or [])]
        plan_dest_types = plan.destination_types or []
        
        origin_match = False
        if plan_origins:
            if deal_origin in plan_origins:
                origin_match = True
                score += 30
            else:
                for po in plan_origins:
                    if deal_origin in DestinationService.get_similar_airports(po):
                        origin_match = True
                        score += 15
                        break
        else:
            origin_match = True
            score += 10
        
        dest_match = False
        if plan_dests:
            if deal_dest in plan_dests:
                dest_match = True
                score += 30
            else:
                for pd in plan_dests:
                    if deal_dest in DestinationService.get_similar_airports(pd):
                        dest_match = True
                        score += 20
                        break
        
        if not dest_match and plan_dest_types:
            if DestinationTypeService.match_deal_to_types(deal_dest, deal_title, plan_dest_types):
                dest_match = True
                score += 25
        
        if not plan_dests and not plan_dest_types:
            dest_match = True
            score += 10
        
        if not origin_match or not dest_match:
            return 0.0
        
        if plan.budget_max and deal.parsed_price:
            deal_price = deal.parsed_price
            deal_currency = deal.parsed_currency or "USD"
            
            if deal_currency != plan.budget_currency:
                converted = CurrencyService.convert_sync(
                    deal_price, deal_currency, plan.budget_currency
                )
                if converted:
                    deal_price = converted
            
            if deal_price <= plan.budget_max:
                savings_pct = (plan.budget_max - deal_price) / plan.budget_max
                score += 20 + (savings_pct * 20)
            else:
                over_budget_pct = (deal_price - plan.budget_max) / plan.budget_max
                if over_budget_pct > 0.2:
                    return 0.0
                score -= over_budget_pct * 30
        
        if plan.cabin_classes:
            deal_cabin = (deal.parsed_cabin_class or "economy").lower()
            if deal_cabin in [c.lower() for c in plan.cabin_classes]:
                score += 10
        
        return max(0.0, score)
    
    def get_matches_for_plan(self, plan_id: int, limit: int = 50) -> list[tuple[Deal, float]]:
        plan = self.db.query(TripPlan).filter(TripPlan.id == plan_id).first()
        if not plan:
            return []
        
        deals = self.db.query(Deal).filter(
            Deal.is_relevant == True
        ).order_by(Deal.published_at.desc()).limit(200).all()
        
        matches = []
        for deal in deals:
            score = self._score_match(deal, plan)
            if score > 0:
                matches.append((deal, score))
        
        matches.sort(key=lambda x: -x[1])
        return matches[:limit]
    
    def update_plan_matches(self, plan: TripPlan) -> int:
        deals = self.db.query(Deal).filter(
            Deal.is_relevant == True
        ).order_by(Deal.published_at.desc()).limit(100).all()
        
        match_count = 0
        for deal in deals:
            score = self._score_match(deal, plan)
            if score > 0:
                match_count += 1
        
        plan.match_count = match_count
        if match_count > 0:
            plan.last_match_at = datetime.utcnow()
        
        self.db.commit()
        return match_count
