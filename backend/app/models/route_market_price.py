from sqlalchemy import Column, Integer, String, DateTime, Float, Index
from sqlalchemy.sql import func
from app.database import Base


class RouteMarketPrice(Base):
    __tablename__ = "route_market_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    
    origin = Column(String(3), nullable=False, index=True)
    destination = Column(String(3), nullable=False, index=True)
    cabin_class = Column(String(20), nullable=False, default="economy")
    
    market_price = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="NZD")
    
    source = Column(String(50), nullable=False)
    month = Column(Integer, nullable=False)
    
    sample_count = Column(Integer, default=1)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    
    checked_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_route_market_lookup', 'origin', 'destination', 'cabin_class', 'month'),
    )
