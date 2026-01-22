from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum, UniqueConstraint, Boolean, Float
from sqlalchemy.sql import func
from app.database import Base
import enum


class DealSource(enum.Enum):
    SECRET_FLYING = "secret_flying"
    OMAAT = "omaat"
    TPG = "the_points_guy"
    THE_FLIGHT_DEAL = "the_flight_deal"
    FLY4FREE = "fly4free"
    GOING = "going"
    HOLIDAY_PIRATES = "holiday_pirates"
    AFF = "australian_frequent_flyer"
    POINT_HACKS = "point_hacks"
    FRUGAL_FLYER = "frugal_flyer"
    SECRET_FLYING_EU = "secret_flying_eu"
    TRAVEL_FREE = "travel_free"


class ParseStatus(enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    PENDING = "pending"


class Deal(Base):
    __tablename__ = "deals"
    
    id = Column(Integer, primary_key=True, index=True)
    
    source = Column(SQLEnum(DealSource), nullable=False, index=True)
    guid = Column(String(512), nullable=True)
    link = Column(String(1024), nullable=False)
    published_at = Column(DateTime, nullable=True)
    
    raw_title = Column(Text, nullable=False)
    raw_summary = Column(Text, nullable=True)
    raw_content_html = Column(Text, nullable=True)
    
    parsed_origin = Column(String(10), nullable=True, index=True)
    parsed_destination = Column(String(10), nullable=True, index=True)
    parsed_price = Column(Integer, nullable=True)
    parsed_currency = Column(String(3), nullable=True)
    parsed_travel_dates = Column(String(256), nullable=True)
    parsed_airline = Column(String(128), nullable=True)
    parsed_cabin_class = Column(String(32), nullable=True)
    
    parse_status = Column(SQLEnum(ParseStatus), default=ParseStatus.PENDING)
    parse_error = Column(Text, nullable=True)
    parse_version = Column(Integer, default=1)
    
    is_relevant = Column(Boolean, default=False, index=True)
    relevance_reason = Column(String(256), nullable=True)
    score = Column(Float, default=0.0, index=True)
    
    fetched_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('source', 'link', name='uix_source_link'),
    )
    
    def is_relevant_to_origin(self, home_airport: str) -> bool:
        if not self.parsed_origin:
            return False
        return self.parsed_origin.upper() == home_airport.upper()
