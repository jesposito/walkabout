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


def mask_api_key(key: str | None) -> str | None:
    """Mask API key for display, showing only last 4 chars."""
    if not key or len(key) < 8:
        return None
    return f"{'*' * (len(key) - 4)}{key[-4:]}"


class SettingsUpdate(BaseModel):
    home_airport: Optional[str] = None
    home_airports: Optional[list[str]] = None
    home_region: Optional[str] = None
    watched_destinations: Optional[list[str]] = None
    watched_regions: Optional[list[str]] = None
    preferred_currency: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    notification_min_discount_percent: Optional[int] = None
    anthropic_api_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    skyscanner_api_key: Optional[str] = None
    amadeus_client_id: Optional[str] = None
    amadeus_client_secret: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_ollama_url: Optional[str] = None
    ai_model: Optional[str] = None


class SettingsResponse(BaseModel):
    home_airport: str
    home_airports: list[str]
    home_region: str
    watched_destinations: list[str]
    watched_regions: list[str]
    preferred_currency: str
    notifications_enabled: bool
    notification_min_discount_percent: int
    anthropic_api_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    skyscanner_api_key: Optional[str] = None
    amadeus_client_id: Optional[str] = None
    amadeus_client_secret: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_ollama_url: Optional[str] = None
    ai_model: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.get("/api/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    settings = UserSettings.get_or_create(db)
    home_airports = settings.home_airports or []
    if not home_airports and settings.home_airport:
        home_airports = [settings.home_airport]
    return SettingsResponse(
        home_airport=settings.home_airport,
        home_airports=home_airports,
        home_region=settings.home_region,
        watched_destinations=settings.watched_destinations or [],
        watched_regions=settings.watched_regions or [],
        preferred_currency=settings.preferred_currency or "NZD",
        notifications_enabled=settings.notifications_enabled,
        notification_min_discount_percent=settings.notification_min_discount_percent,
        anthropic_api_key=mask_api_key(settings.anthropic_api_key),
        serpapi_key=mask_api_key(settings.serpapi_key),
        skyscanner_api_key=mask_api_key(settings.skyscanner_api_key),
        amadeus_client_id=mask_api_key(settings.amadeus_client_id),
        amadeus_client_secret=mask_api_key(settings.amadeus_client_secret),
        ai_provider=settings.ai_provider or "none",
        ai_api_key=mask_api_key(settings.ai_api_key),
        ai_ollama_url=settings.ai_ollama_url,
        ai_model=settings.ai_model,
    )


@router.put("/api/settings", response_model=SettingsResponse)
async def update_settings(
    updates: SettingsUpdate,
    db: Session = Depends(get_db),
):
    settings = UserSettings.get_or_create(db)
    
    if updates.home_airport is not None:
        settings.home_airport = updates.home_airport.upper().strip()
    if updates.home_airports is not None:
        settings.home_airports = [a.upper().strip() for a in updates.home_airports]
        if settings.home_airports:
            settings.home_airport = settings.home_airports[0]
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
    
    # Handle API keys - only update if a new value is provided (not masked placeholder)
    if updates.anthropic_api_key is not None and not updates.anthropic_api_key.startswith("*"):
        settings.anthropic_api_key = updates.anthropic_api_key.strip() if updates.anthropic_api_key else None
    if updates.serpapi_key is not None and not updates.serpapi_key.startswith("*"):
        settings.serpapi_key = updates.serpapi_key.strip() if updates.serpapi_key else None
    if updates.skyscanner_api_key is not None and not updates.skyscanner_api_key.startswith("*"):
        settings.skyscanner_api_key = updates.skyscanner_api_key.strip() if updates.skyscanner_api_key else None
    if updates.amadeus_client_id is not None and not updates.amadeus_client_id.startswith("*"):
        settings.amadeus_client_id = updates.amadeus_client_id.strip() if updates.amadeus_client_id else None
    if updates.amadeus_client_secret is not None and not updates.amadeus_client_secret.startswith("*"):
        settings.amadeus_client_secret = updates.amadeus_client_secret.strip() if updates.amadeus_client_secret else None
    
    if updates.ai_provider is not None:
        settings.ai_provider = updates.ai_provider.lower().strip()
    if updates.ai_api_key is not None and not updates.ai_api_key.startswith("*"):
        settings.ai_api_key = updates.ai_api_key.strip() if updates.ai_api_key else None
    if updates.ai_ollama_url is not None:
        settings.ai_ollama_url = updates.ai_ollama_url.strip() if updates.ai_ollama_url else None
    if updates.ai_model is not None:
        settings.ai_model = updates.ai_model.strip() if updates.ai_model else None
    
    db.commit()
    db.refresh(settings)
    
    relevance = RelevanceService(db)
    updated_count = relevance.update_all_deals()
    
    home_airports = settings.home_airports or []
    if not home_airports and settings.home_airport:
        home_airports = [settings.home_airport]
    return SettingsResponse(
        home_airport=settings.home_airport,
        home_airports=home_airports,
        home_region=settings.home_region,
        watched_destinations=settings.watched_destinations or [],
        watched_regions=settings.watched_regions or [],
        preferred_currency=settings.preferred_currency or "NZD",
        notifications_enabled=settings.notifications_enabled,
        notification_min_discount_percent=settings.notification_min_discount_percent,
        anthropic_api_key=mask_api_key(settings.anthropic_api_key),
        serpapi_key=mask_api_key(settings.serpapi_key),
        skyscanner_api_key=mask_api_key(settings.skyscanner_api_key),
        amadeus_client_id=mask_api_key(settings.amadeus_client_id),
        amadeus_client_secret=mask_api_key(settings.amadeus_client_secret),
        ai_provider=settings.ai_provider or "none",
        ai_api_key=mask_api_key(settings.ai_api_key),
        ai_ollama_url=settings.ai_ollama_url,
        ai_model=settings.ai_model,
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
