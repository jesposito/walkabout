from fastapi import APIRouter, Depends, Request, Query
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
from app.utils.version import get_version

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
    notification_provider: Optional[str] = None
    notification_ntfy_url: Optional[str] = None
    notification_ntfy_topic: Optional[str] = None
    notification_discord_webhook: Optional[str] = None
    notification_min_discount_percent: Optional[int] = None
    notification_quiet_hours_start: Optional[int] = None
    notification_quiet_hours_end: Optional[int] = None
    notification_cooldown_minutes: Optional[int] = None
    timezone: Optional[str] = None
    # Granular notification toggles
    notify_deals: Optional[bool] = None
    notify_trip_matches: Optional[bool] = None
    notify_route_updates: Optional[bool] = None
    notify_system: Optional[bool] = None
    # Deal notification filters
    deal_notify_min_rating: Optional[int] = None
    deal_notify_categories: Optional[list[str]] = None
    deal_notify_cabin_classes: Optional[list[str]] = None
    # Frequency controls
    deal_cooldown_minutes: Optional[int] = None
    trip_cooldown_hours: Optional[int] = None
    route_cooldown_hours: Optional[int] = None
    # Daily digest
    daily_digest_enabled: Optional[bool] = None
    daily_digest_hour: Optional[int] = None
    # API keys
    anthropic_api_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    skyscanner_api_key: Optional[str] = None
    amadeus_client_id: Optional[str] = None
    amadeus_client_secret: Optional[str] = None
    seats_aero_api_key: Optional[str] = None
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
    notification_provider: str = "none"
    notification_ntfy_url: Optional[str] = None
    notification_ntfy_topic: Optional[str] = None
    notification_discord_webhook: Optional[str] = None
    notification_min_discount_percent: int
    notification_quiet_hours_start: Optional[int] = None
    notification_quiet_hours_end: Optional[int] = None
    notification_cooldown_minutes: int = 60
    timezone: str = "Pacific/Auckland"
    # Granular notification toggles
    notify_deals: bool = True
    notify_trip_matches: bool = True
    notify_route_updates: bool = True
    notify_system: bool = True
    # Deal notification filters
    deal_notify_min_rating: int = 3
    deal_notify_categories: list[str] = ["local", "regional"]
    deal_notify_cabin_classes: list[str] = ["economy", "premium_economy", "business", "first"]
    # Frequency controls
    deal_cooldown_minutes: int = 60
    trip_cooldown_hours: int = 6
    route_cooldown_hours: int = 24
    # Daily digest
    daily_digest_enabled: bool = False
    daily_digest_hour: int = 8
    # API keys
    anthropic_api_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    skyscanner_api_key: Optional[str] = None
    amadeus_client_id: Optional[str] = None
    amadeus_client_secret: Optional[str] = None
    seats_aero_api_key: Optional[str] = None
    ai_provider: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_ollama_url: Optional[str] = None
    ai_model: Optional[str] = None

    class Config:
        from_attributes = True


def build_settings_response(settings: UserSettings) -> SettingsResponse:
    """Build a SettingsResponse from UserSettings model."""
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
        notification_provider=settings.notification_provider or "none",
        notification_ntfy_url=settings.notification_ntfy_url,
        notification_ntfy_topic=settings.notification_ntfy_topic,
        notification_discord_webhook=mask_api_key(settings.notification_discord_webhook),
        notification_min_discount_percent=settings.notification_min_discount_percent or 20,
        notification_quiet_hours_start=settings.notification_quiet_hours_start,
        notification_quiet_hours_end=settings.notification_quiet_hours_end,
        notification_cooldown_minutes=settings.notification_cooldown_minutes or 60,
        timezone=settings.timezone or "Pacific/Auckland",
        # Granular notification toggles
        notify_deals=settings.notify_deals if settings.notify_deals is not None else True,
        notify_trip_matches=settings.notify_trip_matches if settings.notify_trip_matches is not None else True,
        notify_route_updates=settings.notify_route_updates if settings.notify_route_updates is not None else True,
        notify_system=settings.notify_system if settings.notify_system is not None else True,
        # Deal notification filters
        deal_notify_min_rating=settings.deal_notify_min_rating or 3,
        deal_notify_categories=settings.deal_notify_categories or ["local", "regional"],
        deal_notify_cabin_classes=settings.deal_notify_cabin_classes or ["economy", "premium_economy", "business", "first"],
        # Frequency controls
        deal_cooldown_minutes=settings.deal_cooldown_minutes or 60,
        trip_cooldown_hours=settings.trip_cooldown_hours or 6,
        route_cooldown_hours=settings.route_cooldown_hours or 24,
        # Daily digest
        daily_digest_enabled=settings.daily_digest_enabled if settings.daily_digest_enabled is not None else False,
        daily_digest_hour=settings.daily_digest_hour or 8,
        # API keys
        anthropic_api_key=mask_api_key(settings.anthropic_api_key),
        serpapi_key=mask_api_key(settings.serpapi_key),
        skyscanner_api_key=mask_api_key(settings.skyscanner_api_key),
        amadeus_client_id=mask_api_key(settings.amadeus_client_id),
        amadeus_client_secret=mask_api_key(settings.amadeus_client_secret),
        seats_aero_api_key=mask_api_key(settings.seats_aero_api_key),
        ai_provider=settings.ai_provider or "none",
        ai_api_key=mask_api_key(settings.ai_api_key),
        ai_ollama_url=settings.ai_ollama_url,
        ai_model=settings.ai_model,
    )


@router.get("/api/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    settings = UserSettings.get_or_create(db)
    return build_settings_response(settings)


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
    if updates.notification_provider is not None:
        settings.notification_provider = updates.notification_provider
    if updates.notification_ntfy_url is not None:
        settings.notification_ntfy_url = updates.notification_ntfy_url.strip() if updates.notification_ntfy_url else None
    if updates.notification_ntfy_topic is not None:
        settings.notification_ntfy_topic = updates.notification_ntfy_topic.strip() if updates.notification_ntfy_topic else None
    if updates.notification_discord_webhook is not None and not updates.notification_discord_webhook.startswith("*"):
        settings.notification_discord_webhook = updates.notification_discord_webhook.strip() if updates.notification_discord_webhook else None
    if updates.notification_min_discount_percent is not None:
        settings.notification_min_discount_percent = updates.notification_min_discount_percent
    if updates.notification_quiet_hours_start is not None:
        settings.notification_quiet_hours_start = updates.notification_quiet_hours_start
    if updates.notification_quiet_hours_end is not None:
        settings.notification_quiet_hours_end = updates.notification_quiet_hours_end
    if updates.notification_cooldown_minutes is not None:
        settings.notification_cooldown_minutes = updates.notification_cooldown_minutes
    if updates.timezone is not None:
        settings.timezone = updates.timezone.strip()

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
    if updates.seats_aero_api_key is not None and not updates.seats_aero_api_key.startswith("*"):
        settings.seats_aero_api_key = updates.seats_aero_api_key.strip() if updates.seats_aero_api_key else None

    if updates.ai_provider is not None:
        settings.ai_provider = updates.ai_provider.lower().strip()
    if updates.ai_api_key is not None and not updates.ai_api_key.startswith("*"):
        settings.ai_api_key = updates.ai_api_key.strip() if updates.ai_api_key else None
    if updates.ai_ollama_url is not None:
        settings.ai_ollama_url = updates.ai_ollama_url.strip() if updates.ai_ollama_url else None
    if updates.ai_model is not None:
        settings.ai_model = updates.ai_model.strip() if updates.ai_model else None

    # Granular notification toggles
    if updates.notify_deals is not None:
        settings.notify_deals = updates.notify_deals
    if updates.notify_trip_matches is not None:
        settings.notify_trip_matches = updates.notify_trip_matches
    if updates.notify_route_updates is not None:
        settings.notify_route_updates = updates.notify_route_updates
    if updates.notify_system is not None:
        settings.notify_system = updates.notify_system

    # Deal notification filters
    if updates.deal_notify_min_rating is not None:
        settings.deal_notify_min_rating = max(1, min(5, updates.deal_notify_min_rating))
    if updates.deal_notify_categories is not None:
        settings.deal_notify_categories = updates.deal_notify_categories
    if updates.deal_notify_cabin_classes is not None:
        settings.deal_notify_cabin_classes = updates.deal_notify_cabin_classes

    # Frequency controls
    if updates.deal_cooldown_minutes is not None:
        settings.deal_cooldown_minutes = max(0, updates.deal_cooldown_minutes)
    if updates.trip_cooldown_hours is not None:
        settings.trip_cooldown_hours = max(0, updates.trip_cooldown_hours)
    if updates.route_cooldown_hours is not None:
        settings.route_cooldown_hours = max(0, updates.route_cooldown_hours)

    # Daily digest
    if updates.daily_digest_enabled is not None:
        settings.daily_digest_enabled = updates.daily_digest_enabled
    if updates.daily_digest_hour is not None:
        settings.daily_digest_hour = max(0, min(23, updates.daily_digest_hour))

    db.commit()
    db.refresh(settings)

    relevance = RelevanceService(db)
    updated_count = relevance.update_all_deals()

    return build_settings_response(settings)


@router.get("/legacy", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    settings = UserSettings.get_or_create(db)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "version": get_version(),
        }
    )


@router.post("/api/review")
async def ai_review_settings(db: Session = Depends(get_db)):
    """AI-powered review and optimization of user settings."""
    from app.services.ai_service import AIService
    from fastapi import HTTPException
    if not AIService.is_configured():
        raise HTTPException(status_code=503, detail="AI service is not configured")

    settings = UserSettings.get_or_create(db)

    from app.services.ai_deals import review_settings
    result = await review_settings(settings, db=db)
    return result


@router.get("/api/review/estimate")
async def ai_review_settings_estimate(db: Session = Depends(get_db)):
    """Return token/cost estimate for a settings review without running the AI."""
    from app.services.ai_service import AIService
    from fastapi import HTTPException
    if not AIService.is_configured():
        raise HTTPException(status_code=503, detail="AI service is not configured")

    settings = UserSettings.get_or_create(db)

    from app.services.ai_deals import estimate_settings_review
    return estimate_settings_review(settings)


@router.post("/api/notifications/test")
async def test_notification(db: Session = Depends(get_db)):
    """Send a test notification via the configured provider."""
    from app.services.notification import get_global_notifier

    settings = UserSettings.get_or_create(db)
    notifier = get_global_notifier()
    success, message = await notifier.send_test_notification(user_settings=settings)
    provider = settings.notification_provider or "none"
    return {"success": success, "message": message, "provider": provider}


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


@router.get("/api/airports/bulk")
async def bulk_lookup_airports(codes: str = Query("")):
    """Lookup multiple airports by comma-separated codes. Returns {code: {city, country}} map."""
    code_list = [c.strip().upper() for c in codes.split(",") if c.strip()]
    result = {}
    for code in code_list[:100]:  # Cap at 100 codes
        airport = AirportService.get(code)
        if airport:
            result[code] = {"city": airport.city, "country": airport.country}
    return result


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
