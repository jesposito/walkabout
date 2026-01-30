"""
TripPlanMatch - Persists the best flight matches for each Trip Plan.

This model unifies matches from all sources (Google Flights, RSS deals, etc.)
so users see a single consolidated view of the best options for their trip.
"""

from enum import Enum
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class MatchSource(str, Enum):
    """Source of a trip plan match."""
    GOOGLE_FLIGHTS = "google_flights"
    RSS_DEAL = "rss_deal"
    SEATS_AERO = "seats_aero"
    AMADEUS = "amadeus"


class TripPlanMatch(Base):
    """
    A persisted match for a Trip Plan from any source.
    
    Each Trip Plan keeps its top N matches (typically 5), updated on each
    scheduled search. This gives users a consolidated view of the best
    options regardless of source.
    """
    __tablename__ = "trip_plan_matches"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Link to trip plan
    trip_plan_id = Column(
        Integer,
        ForeignKey("trip_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Source of this match
    source = Column(String(50), nullable=False, default=MatchSource.GOOGLE_FLIGHTS.value)
    
    # If from RSS deal, link to the deal
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)
    
    # Route info
    origin = Column(String(10), nullable=False)
    destination = Column(String(10), nullable=False)
    
    # Dates
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    
    # Price (always in NZD for consistent comparison)
    price_nzd = Column(Numeric(10, 2), nullable=False)
    original_price = Column(Numeric(10, 2), nullable=True)  # Price before conversion
    original_currency = Column(String(3), nullable=True)
    
    # Flight details
    airline = Column(String(100), nullable=True)
    stops = Column(Integer, default=0)
    duration_minutes = Column(Integer, nullable=True)
    
    # Booking link
    booking_url = Column(Text, nullable=True)
    
    # Match quality score (0-100, used for ranking)
    match_score = Column(Numeric(5, 2), default=50.0)
    
    # Deal title (for RSS deals)
    deal_title = Column(String(500), nullable=True)
    
    # Timestamps
    found_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    trip_plan = relationship("TripPlan", back_populates="matches")
    deal = relationship("Deal", foreign_keys=[deal_id])
    
    def __repr__(self) -> str:
        return f"<TripPlanMatch {self.id}: {self.origin}->{self.destination} ${self.price_nzd} ({self.source})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if this match's departure date has passed."""
        from datetime import date
        return self.departure_date < date.today()
    
    @property
    def days_until_departure(self) -> int:
        """Days until departure (negative if past)."""
        from datetime import date
        return (self.departure_date - date.today()).days
