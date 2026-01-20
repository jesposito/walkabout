from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RouteBase(BaseModel):
    origin: str
    destination: str
    name: Optional[str] = None
    is_active: bool = True
    scrape_frequency_hours: int = 12


class RouteCreate(RouteBase):
    pass


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    scrape_frequency_hours: Optional[int] = None


class RouteResponse(RouteBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
