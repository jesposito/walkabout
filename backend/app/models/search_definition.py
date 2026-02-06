from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class TripType(str, enum.Enum):
    ROUND_TRIP = "round_trip"
    ONE_WAY = "one_way"


class CabinClass(str, enum.Enum):
    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class StopsFilter(str, enum.Enum):
    ANY = "any"
    NONSTOP = "nonstop"
    ONE_STOP = "one_stop"
    TWO_PLUS = "two_plus"


class SearchDefinition(Base):
    """
    Fully specifies what a price series means - any change creates a new version.
    
    This is the entity that makes price history comparable. Two prices are only
    comparable if they share the same search_definition_id.
    
    Oracle Review: "Without persisting full query parameters, history becomes non-comparable."
    """
    __tablename__ = "search_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Route
    origin = Column(String(3), nullable=False, index=True)  # IATA code
    destination = Column(String(3), nullable=False, index=True)  # IATA code
    
    # Trip type
    trip_type = Column(SQLEnum(TripType), default=TripType.ROUND_TRIP, nullable=False)
    
    # Dates - for flexible date monitoring, store as "days from now" pattern
    # e.g., "departure in 60-90 days, return 7-14 days later"
    departure_date_start = Column(Date, nullable=True)  # Fixed date mode
    departure_date_end = Column(Date, nullable=True)    # Fixed date mode
    departure_days_min = Column(Integer, nullable=True)  # Rolling window mode (days from now)
    departure_days_max = Column(Integer, nullable=True)  # Rolling window mode
    trip_duration_days_min = Column(Integer, nullable=True)  # For round trips
    trip_duration_days_max = Column(Integer, nullable=True)
    
    # Passengers
    adults = Column(Integer, default=2, nullable=False)
    children = Column(Integer, default=2, nullable=False)  # Ages 2-11
    infants_in_seat = Column(Integer, default=0, nullable=False)
    infants_on_lap = Column(Integer, default=0, nullable=False)
    
    # Cabin and stops
    cabin_class = Column(SQLEnum(CabinClass), default=CabinClass.ECONOMY, nullable=False)
    stops_filter = Column(SQLEnum(StopsFilter), default=StopsFilter.ANY, nullable=False)
    
    # Airline filters (comma-separated IATA codes, or null for any)
    include_airlines = Column(String(100), nullable=True)  # e.g., "NZ,QF,HA"
    exclude_airlines = Column(String(100), nullable=True)
    
    # Locale/currency (affects prices shown)
    currency = Column(String(3), default="USD", nullable=False)
    locale = Column(String(10), default="en-US", nullable=False)  # Affects point of sale
    
    # Bags (Google Flights can filter by bags included)
    carry_on_bags = Column(Integer, default=0, nullable=False)
    checked_bags = Column(Integer, default=0, nullable=False)
    
    # Metadata
    name = Column(String(100), nullable=True)  # Human-friendly name
    is_active = Column(Boolean, default=True, nullable=False)
    scrape_frequency_hours = Column(Integer, default=12, nullable=False)
    preferred_source = Column(String(20), default="auto", nullable=False)  # auto, serpapi, skyscanner, amadeus, playwright
    
    # Version tracking - if parameters change, create new definition
    version = Column(Integer, default=1, nullable=False)
    parent_id = Column(Integer, nullable=True)  # Reference to previous version if changed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    prices = relationship("FlightPrice", back_populates="search_definition")
    scrape_health = relationship("ScrapeHealth", back_populates="search_definition", uselist=False)
    
    @property
    def total_passengers(self) -> int:
        return self.adults + self.children + self.infants_in_seat + self.infants_on_lap
    
    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        return f"{self.origin}-{self.destination} ({self.total_passengers}pax, {self.cabin_class.value})"
    
    def __repr__(self) -> str:
        return f"<SearchDefinition {self.id}: {self.display_name}>"
