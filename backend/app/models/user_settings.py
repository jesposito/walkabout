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
    seats_aero_api_key = Column(String(200), nullable=True)
    
    ai_provider = Column(String(20), default="none")
    ai_api_key = Column(String(200), nullable=True)
    ai_ollama_url = Column(String(200), nullable=True)
    ai_model = Column(String(50), nullable=True)
    
    notifications_enabled = Column(Boolean, default=False)
    notification_provider = Column(String(20), default="none")  # none, ntfy_self, ntfy_sh, discord
    notification_ntfy_url = Column(String(200), nullable=True)  # For self-hosted ntfy
    notification_ntfy_topic = Column(String(100), nullable=True)
    notification_discord_webhook = Column(String(300), nullable=True)
    notification_min_discount_percent = Column(Integer, default=20)
    notification_quiet_hours_start = Column(Integer, nullable=True)  # Hour 0-23, e.g., 22 for 10 PM
    notification_quiet_hours_end = Column(Integer, nullable=True)    # Hour 0-23, e.g., 7 for 7 AM
    notification_cooldown_minutes = Column(Integer, default=60)      # Min time between notifications
    timezone = Column(String(50), default="Pacific/Auckland")

    # Granular notification toggles
    notify_deals = Column(Boolean, default=True)           # Flight deal alerts
    notify_trip_matches = Column(Boolean, default=True)    # Trip plan match alerts
    notify_route_updates = Column(Boolean, default=True)   # Route price change alerts
    notify_system = Column(Boolean, default=True)          # System alerts (errors, startup)

    # Deal notification filters
    deal_notify_min_rating = Column(Integer, default=3)    # 1-5, only notify deals rated >= this
    deal_notify_categories = Column(JSON, default=lambda: ["local", "regional"])  # local, regional, hub
    deal_notify_cabin_classes = Column(JSON, default=lambda: ["economy", "premium_economy", "business", "first"])

    # Frequency controls
    deal_cooldown_minutes = Column(Integer, default=60)    # Per-route deal cooldown
    trip_cooldown_hours = Column(Integer, default=6)       # Trip match cooldown
    route_cooldown_hours = Column(Integer, default=24)     # Route update cooldown

    # Daily digest option
    daily_digest_enabled = Column(Boolean, default=False)  # Send daily summary instead of instant
    daily_digest_hour = Column(Integer, default=8)         # Hour to send digest (0-23)

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
