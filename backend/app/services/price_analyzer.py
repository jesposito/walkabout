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
    robust_z_score: float  # Using median/MAD
    mean_price: Decimal
    median_price: Decimal  # Added for robust analysis
    stddev_price: Decimal
    mad_price: Decimal  # Median Absolute Deviation
    price_vs_mean: Decimal
    price_vs_median: Decimal  # Added
    percentile: float
    history_count: int
    reason: str
    is_new_low: bool = False  # Absolute new low independent of z-score


def robust_z_score(current_price: float, history: List[float]) -> float:
    """
    Calculate robust z-score using median + MAD instead of mean + stddev.
    
    Oracle Review: "Flight pricing is non-stationary and discontinuous. 
    Mean/stddev can be skewed by spikes."
    
    MAD (Median Absolute Deviation) is more robust to outliers than standard deviation.
    The scale factor 1.4826 makes MAD comparable to stddev for normal distributions.
    
    Args:
        current_price: The price to evaluate
        history: List of historical prices
    
    Returns:
        Robust z-score (negative = below median = potentially good deal)
    """
    if len(history) < 2:
        return 0.0
    
    median = statistics.median(history)
    
    # Calculate MAD (Median Absolute Deviation)
    deviations = [abs(x - median) for x in history]
    mad = statistics.median(deviations)
    
    # Prevent division by zero
    # Scale factor 1.4826 makes MAD comparable to stddev for normal distributions
    if mad == 0:
        # All values are the same - any deviation is significant
        # Use a small value to prevent division by zero
        mad = 0.01 * median if median > 0 else 1.0
    
    scaled_mad = mad * 1.4826
    
    return (current_price - median) / scaled_mad


def calculate_percentile(price: float, history: List[float]) -> float:
    """
    Calculate what percentile this price falls at.
    Lower percentile = better deal.
    
    Returns value from 0-100 where:
    - 0 = lowest price ever
    - 100 = highest price ever
    - 50 = median
    """
    if not history:
        return 50.0
    
    below_count = sum(1 for p in history if p >= price)
    return (below_count / len(history)) * 100


def is_absolute_new_low(price: float, history: List[float], margin_percent: float = 2.0) -> bool:
    """
    Check if this price is a new absolute low (within margin).
    
    Oracle Review: "'New absolute low' alert independent of z-score"
    
    Args:
        price: Current price
        history: Historical prices
        margin_percent: Consider "new low" if within this % of historical min
    
    Returns:
        True if price is at or below historical minimum (with margin)
    """
    if not history:
        return False
    
    historical_min = min(history)
    threshold = historical_min * (1 + margin_percent / 100)
    
    return price <= threshold


class PriceAnalyzer:
    def __init__(self, db: Session):
        self.db = db
    
    def get_price_history(
        self,
        search_definition_id: int,
        days: int = 90,
    ) -> List[float]:
        """
        Get price history for a search definition.
        
        Note: Now uses search_definition_id instead of route_id for proper
        price comparability.
        """
        prices = self.db.query(FlightPrice.price_nzd).filter(
            FlightPrice.search_definition_id == search_definition_id,
            FlightPrice.scraped_at >= func.now() - timedelta(days=days)
        ).all()
        
        return [float(p[0]) for p in prices]
    
    def analyze_price(self, price: FlightPrice) -> DealAnalysis:
        """
        Analyze whether a price represents a deal.
        
        Uses both traditional z-score and robust z-score (median/MAD).
        """
        history = self.get_price_history(price.search_definition_id)
        current_price = float(price.price_nzd)
        
        # Insufficient history check
        if len(history) < settings.min_history_for_analysis:
            return DealAnalysis(
                is_deal=False,
                z_score=0.0,
                robust_z_score=0.0,
                mean_price=Decimal(0),
                median_price=Decimal(0),
                stddev_price=Decimal(0),
                mad_price=Decimal(0),
                price_vs_mean=Decimal(0),
                price_vs_median=Decimal(0),
                percentile=50.0,
                history_count=len(history),
                reason=f"Insufficient history ({len(history)} < {settings.min_history_for_analysis})",
                is_new_low=False
            )
        
        # Calculate traditional stats
        mean = statistics.mean(history)
        stddev = statistics.stdev(history) if len(history) > 1 else 1.0
        if stddev == 0:
            stddev = 1.0
        traditional_z = (current_price - mean) / stddev
        
        # Calculate robust stats (Oracle recommended)
        median = statistics.median(history)
        deviations = [abs(x - median) for x in history]
        mad = statistics.median(deviations) if deviations else 1.0
        if mad == 0:
            mad = 0.01 * median if median > 0 else 1.0
        
        robust_z = robust_z_score(current_price, history)
        
        # Calculate percentile and new low
        percentile = calculate_percentile(current_price, history)
        new_low = is_absolute_new_low(current_price, history)
        
        # Deal detection: Use robust z-score as primary, traditional as secondary
        # Also flag new absolute lows regardless of z-score
        is_deal = (
            robust_z <= settings.deal_threshold_z_score or
            new_low
        )
        
        # Build reason string
        if new_low:
            reason = f"New low price! (${current_price:.0f} vs historical min ${min(history):.0f})"
        elif robust_z <= settings.deal_threshold_z_score:
            reason = f"Price is {abs(robust_z):.1f} MADs below median (robust z={robust_z:.2f})"
        else:
            reason = f"Price is within normal range (robust z={robust_z:.2f}, traditional z={traditional_z:.2f})"
        
        return DealAnalysis(
            is_deal=is_deal,
            z_score=traditional_z,
            robust_z_score=robust_z,
            mean_price=Decimal(str(round(mean, 2))),
            median_price=Decimal(str(round(median, 2))),
            stddev_price=Decimal(str(round(stddev, 2))),
            mad_price=Decimal(str(round(mad, 2))),
            price_vs_mean=Decimal(str(round(current_price - mean, 2))),
            price_vs_median=Decimal(str(round(current_price - median, 2))),
            percentile=percentile,
            history_count=len(history),
            reason=reason,
            is_new_low=new_low
        )
