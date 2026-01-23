from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, default=1)
    
    home_airport = Column(String(10), default="AKL")  # Legacy - kept for backward compat
    home_airports = Column(JSON, default=list)  # New: list of home airport codes
    home_region = Column(String(50), default="Oceania")
    
    watched_destinations = Column(JSON, default=list)
    watched_regions = Column(JSON, default=list)
    
    preferred_currency = Column(String(3), default="NZD")
    
    anthropic_api_key = Column(String(200), nullable=True)
    serpapi_key = Column(String(100), nullable=True)
    skyscanner_api_key = Column(String(100), nullable=True)
    amadeus_client_id = Column(String(100), nullable=True)
    amadeus_client_secret = Column(String(100), nullable=True)
    
    notifications_enabled = Column(Boolean, default=False)
    notification_min_discount_percent = Column(Integer, default=20)
    
    last_notified_deal_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    @classmethod
    def get_or_create(cls, db):
        settings = db.query(cls).filter(cls.id == 1).first()
        if not settings:
            settings = cls(
                id=1,
                home_airport="AKL",
                home_airports=["AKL"],
                home_region="Oceania",
                watched_destinations=["SYD", "MEL", "NAN", "RAR", "HNL", "TYO", "SIN"],
                watched_regions=["Pacific", "Asia", "Australia"],
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        elif not settings.home_airports:
            settings.home_airports = [settings.home_airport] if settings.home_airport else ["AKL"]
            db.commit()
            db.refresh(settings)
        return settings
