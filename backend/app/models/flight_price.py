from sqlalchemy import Column, BigInteger, Integer, String, Date, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
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
    
    id = Column(BigInteger, primary_key=True, index=True)
    
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
    
    # Price
    price_nzd = Column(Numeric(10, 2), nullable=False)
    
    # Flight details (extracted from scrape)
    airline = Column(String(100), nullable=True)
    stops = Column(Integer, default=0)
    duration_minutes = Column(Integer, nullable=True)
    
    # Raw data for debugging/reprocessing
    raw_data = Column(JSONB, nullable=True)
    
    # Relationships
    search_definition = relationship("SearchDefinition", back_populates="prices")
    
    def __repr__(self) -> str:
        return f"<FlightPrice {self.id}: ${self.price_nzd} on {self.scraped_at}>"
