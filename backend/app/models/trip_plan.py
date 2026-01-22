from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text
from sqlalchemy.sql import func
from app.database import Base


class TripPlan(Base):
    __tablename__ = "trip_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    
    name = Column(String(128), nullable=False)
    
    origins = Column(JSON, default=list)
    
    destinations = Column(JSON, default=list)
    destination_types = Column(JSON, default=list)
    
    available_from = Column(DateTime, nullable=True)
    available_to = Column(DateTime, nullable=True)
    
    trip_duration_min = Column(Integer, default=3)
    trip_duration_max = Column(Integer, default=14)
    
    budget_max = Column(Integer, nullable=True)
    budget_currency = Column(String(3), default="NZD")
    
    travelers_adults = Column(Integer, default=2)
    travelers_children = Column(Integer, default=0)
    cabin_classes = Column(JSON, default=list)
    
    is_active = Column(Boolean, default=True)
    notify_on_match = Column(Boolean, default=True)
    
    # How often to check for matching deals (hours)
    check_frequency_hours = Column(Integer, default=12)
    
    notes = Column(Text, nullable=True)
    
    match_count = Column(Integer, default=0)
    last_match_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
