from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    flight_price_id = Column(Integer, ForeignKey("flight_prices.id"))
    alert_type = Column(String(50), nullable=False)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    price_nzd = Column(Numeric(10, 2))
    z_score = Column(Numeric(5, 2))
    message = Column(Text)
    ai_analysis = Column(Text)
