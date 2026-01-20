from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Route(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, index=True)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    name = Column(String(100))
    is_active = Column(Boolean, default=True)
    scrape_frequency_hours = Column(Integer, default=12)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
