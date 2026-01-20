from sqlalchemy import Column, BigInteger, Integer, String, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class FlightPrice(Base):
    __tablename__ = "flight_prices"
    
    id = Column(BigInteger, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False, index=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=False)
    price_nzd = Column(Numeric(10, 2), nullable=False)
    airline = Column(String(100))
    stops = Column(Integer, default=0)
    cabin_class = Column(String(20), default="economy")
    passengers = Column(Integer, default=4)
    raw_data = Column(JSONB)
