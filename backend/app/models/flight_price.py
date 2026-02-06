from sqlalchemy import Column, BigInteger, Boolean, Integer, String, Date, DateTime, Numeric, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class FlightPrice(Base):
    """
    Price data point for a specific search definition at a point in time.
    
    This is a TimescaleDB hypertable partitioned by scraped_at for efficient
    time-series queries.
    
    Oracle Review: "Prices are only comparable if they share the same search_definition_id"
    """
    __tablename__ = "flight_prices"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # Link to search definition (replaces route_id for proper comparability)
    search_definition_id = Column(
        Integer, 
        ForeignKey("search_definitions.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Timestamps
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # The specific dates this price is for
    departure_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)  # Null for one-way
    
    # Price (per person, as shown by Google Flights)
    price_nzd = Column(Numeric(10, 2), nullable=False)
    total_price_nzd = Column(Numeric(10, 2), nullable=True)  # price_nzd * passengers
    passengers = Column(Integer, nullable=True)  # Passenger count used for this search
    trip_type = Column(String(20), nullable=True)  # round_trip or one_way

    # Flight details (extracted from scrape)
    airline = Column(String(100), nullable=True)
    stops = Column(Integer, default=0)
    duration_minutes = Column(Integer, nullable=True)
    layover_airports = Column(String(200), nullable=True)  # Comma-separated IATA codes
    
    # Raw data for debugging/reprocessing
    raw_data = Column(JSON, nullable=True)

    # Data quality (anomaly guard)
    confidence = Column(Numeric(5, 4), nullable=True)
    is_suspicious = Column(Boolean, default=False, server_default='0', nullable=False)

    # Relationships
    search_definition = relationship("SearchDefinition", back_populates="prices")
    
    def __repr__(self) -> str:
        return f"<FlightPrice {self.id}: ${self.price_nzd} on {self.scraped_at}>"
