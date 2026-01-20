from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class FlightPriceResponse(BaseModel):
    id: int
    route_id: int
    scraped_at: datetime
    departure_date: date
    return_date: date
    price_nzd: Decimal
    airline: Optional[str] = None
    stops: int
    cabin_class: str
    passengers: int
    
    class Config:
        from_attributes = True


class PriceStats(BaseModel):
    route_id: int
    min_price: Decimal
    max_price: Decimal
    avg_price: Decimal
    current_price: Optional[Decimal] = None
    price_count: int
    z_score: Optional[float] = None
    percentile: Optional[float] = None
