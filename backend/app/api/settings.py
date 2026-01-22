from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os

from app.database import get_db
from app.models.user_settings import UserSettings
from app.services.relevance import RelevanceService
from app.services.airports import AirportService

router = APIRouter()

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)


class SettingsUpdate(BaseModel):
    home_airport: Optional[str] = None
    home_region: Optional[str] = None
    watched_destinations: Optional[list[str]] = None
    watched_regions: Optional[list[str]] = None
    preferred_currency: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    notification_min_discount_percent: Optional[int] = None


class SettingsResponse(BaseModel):
    home_airport: str
    home_region: str
    watched_destinations: list[str]
    watched_regions: list[str]
    preferred_currency: str
    notifications_enabled: bool
    notification_min_discount_percent: int
    
    class Config:
        from_attributes = True


@router.get("/api/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    settings = UserSettings.get_or_create(db)
    return SettingsResponse(
        home_airport=settings.home_airport,
        home_region=settings.home_region,
        watched_destinations=settings.watched_destinations or [],
        watched_regions=settings.watched_regions or [],
        preferred_currency=settings.preferred_currency or "NZD",
        notifications_enabled=settings.notifications_enabled,
        notification_min_discount_percent=settings.notification_min_discount_percent,
    )


@router.put("/api/settings", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    db: Session = Depends(get_db),
):
    settings = UserSettings.get_or_create(db)
    
    if updates.home_airport is not None:
        settings.home_airport = updates.home_airport.upper().strip()
    if updates.home_region is not None:
        settings.home_region = updates.home_region
    if updates.watched_destinations is not None:
        settings.watched_destinations = [d.upper().strip() for d in updates.watched_destinations]
    if updates.watched_regions is not None:
        settings.watched_regions = updates.watched_regions
    if updates.preferred_currency is not None:
        settings.preferred_currency = updates.preferred_currency.upper().strip()
    if updates.notifications_enabled is not None:
        settings.notifications_enabled = updates.notifications_enabled
    if updates.notification_min_discount_percent is not None:
        settings.notification_min_discount_percent = updates.notification_min_discount_percent
    
    db.commit()
    db.refresh(settings)
    
    relevance = RelevanceService(db)
    updated_count = relevance.update_all_deals()
    
    return SettingsResponse(
        home_airport=settings.home_airport,
        home_region=settings.home_region,
        watched_destinations=settings.watched_destinations or [],
        watched_regions=settings.watched_regions or [],
        preferred_currency=settings.preferred_currency or "NZD",
        notifications_enabled=settings.notifications_enabled,
        notification_min_discount_percent=settings.notification_min_discount_percent,
    )


@router.get("/", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    settings = UserSettings.get_or_create(db)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
        }
    )


@router.get("/api/airports/search")
async def search_airports(q: str, limit: int = 10):
    results = AirportService.search(q, limit)
    return {
        "results": [
            {
                "code": a.code,
                "name": a.name,
                "city": a.city,
                "country": a.country,
                "region": a.region,
                "label": f"{a.code} - {a.city}, {a.country}",
            }
            for a in results
        ]
    }


@router.get("/api/airports/{code}")
async def get_airport(code: str):
    airport = AirportService.get(code)
    if not airport:
        return {"error": "Airport not found"}
    return {
        "code": airport.code,
        "name": airport.name,
        "city": airport.city,
        "country": airport.country,
        "region": airport.region,
    }
