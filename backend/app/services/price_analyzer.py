import statistics
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta
from app.models import FlightPrice
from app.config import get_settings

settings = get_settings()


@dataclass
class DealAnalysis:
    is_deal: bool
    z_score: float
    mean_price: Decimal
    stddev_price: Decimal
    price_vs_mean: Decimal
    percentile: float
    history_count: int
    reason: str


class PriceAnalyzer:
    def __init__(self, db: Session):
        self.db = db
    
    def get_price_history(
        self,
        route_id: int,
        days: int = 90,
        date_window_days: int = 14
    ) -> List[float]:
        prices = self.db.query(FlightPrice.price_nzd).filter(
            FlightPrice.route_id == route_id,
            FlightPrice.scraped_at >= func.now() - timedelta(days=days)
        ).all()
        
        return [float(p[0]) for p in prices]
    
    def calculate_percentile(self, price: float, history: List[float]) -> float:
        if not history:
            return 50.0
        
        below_count = sum(1 for p in history if p > price)
        return (below_count / len(history)) * 100
    
    def analyze_price(self, price: FlightPrice) -> DealAnalysis:
        history = self.get_price_history(price.route_id)
        current_price = float(price.price_nzd)
        
        if len(history) < settings.min_history_for_analysis:
            return DealAnalysis(
                is_deal=False,
                z_score=0.0,
                mean_price=Decimal(0),
                stddev_price=Decimal(0),
                price_vs_mean=Decimal(0),
                percentile=50.0,
                history_count=len(history),
                reason=f"Insufficient history ({len(history)} < {settings.min_history_for_analysis})"
            )
        
        mean = statistics.mean(history)
        stddev = statistics.stdev(history) if len(history) > 1 else 1.0
        
        if stddev == 0:
            stddev = 1.0
        
        z_score = (current_price - mean) / stddev
        percentile = self.calculate_percentile(current_price, history)
        price_vs_mean = Decimal(str(current_price - mean))
        
        is_deal = z_score <= settings.deal_threshold_z_score
        
        if is_deal:
            reason = f"Price is {abs(z_score):.1f} std devs below average"
        else:
            reason = f"Price is within normal range (z={z_score:.1f})"
        
        return DealAnalysis(
            is_deal=is_deal,
            z_score=z_score,
            mean_price=Decimal(str(mean)),
            stddev_price=Decimal(str(stddev)),
            price_vs_mean=price_vs_mean,
            percentile=percentile,
            history_count=len(history),
            reason=reason
        )
