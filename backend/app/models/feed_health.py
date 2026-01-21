from sqlalchemy import Column, Integer, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database import Base
from app.models.deal import DealSource


class FeedHealth(Base):
    __tablename__ = "feed_health"
    
    id = Column(Integer, primary_key=True, index=True)
    source = Column(SQLEnum(DealSource), unique=True, nullable=False)
    
    last_fetch_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    
    consecutive_failures = Column(Integer, default=0)
    total_items_fetched = Column(Integer, default=0)
    total_items_new = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
