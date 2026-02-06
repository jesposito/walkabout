from fastapi import APIRouter, Depends, Request, Query, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import os
import asyncio
import logging

from app.database import get_db
from app.models.trip_plan import TripPlan
from app.models.trip_plan_match import TripPlanMatch
from app.models.user_settings import UserSettings
from app.services.trip_matcher import TripMatcher
from app.services.currency import CurrencyService
from app.utils.template_helpers import get_airports_dict
from app.utils.version import get_version
from app.services.airports import AIRPORTS, AirportService
from app.services.trip_plan_search import TripPlanSearchService

# Pre-compute airports dict for API responses
airports = {code: {"city": a.city, "country": a.country} for code, a in AIRPORTS.items()}

router = APIRouter()

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)


class TripLegSchema(BaseModel):
    origin: str
    destination: str
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    order: int = 0


class TripPlanCreate(BaseModel):
    name: str
    origins: list[str] = []
    destinations: list[str] = []
    destination_types: list[str] = []
    legs: list[TripLegSchema] = []
    available_from: Optional[datetime] = None
    available_to: Optional[datetime] = None
    trip_duration_min: int = 3
    trip_duration_max: int = 14
    budget_max: Optional[int] = None
    budget_currency: str = "NZD"
    cabin_classes: list[str] = ["economy"]
    travelers_adults: int = 2
    travelers_children: int = 0
    notify_on_match: bool = True
    check_frequency_hours: int = 12
    notes: Optional[str] = None


class TripPlanResponse(BaseModel):
    id: int
    name: str
    origins: list[str]
    destinations: list[str]
    destination_types: list[str]
    available_from: Optional[datetime]
    available_to: Optional[datetime]
    trip_duration_min: int
    trip_duration_max: int
    budget_max: Optional[int]
    budget_currency: str
    cabin_classes: list[str]
    travelers_adults: int
    travelers_children: int
    is_active: bool
    notify_on_match: bool
    check_frequency_hours: int
    match_count: int
    last_match_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    legs: list[dict] = []
    search_in_progress: bool = False

    class Config:
        from_attributes = True


@router.get("/legacy", response_class=HTMLResponse)
async def trips_page(request: Request, db: Session = Depends(get_db)):
    trips = db.query(TripPlan).order_by(TripPlan.created_at.desc()).all()
    settings = UserSettings.get_or_create(db)
    
    trips_with_matches = []
    matcher = TripMatcher(db)
    for trip in trips:
        rss_matches = matcher.get_matches_for_plan(trip.id, limit=5)
        
        best_flights = db.query(TripPlanMatch).filter(
            TripPlanMatch.trip_plan_id == trip.id
        ).order_by(TripPlanMatch.match_score.desc()).limit(5).all()
        
        trips_with_matches.append({
            "trip": trip,
            "top_matches": rss_matches,
            "best_flights": best_flights,
        })
    
    return templates.TemplateResponse(
        "trips.html",
        {
            "request": request,
            "trips": trips_with_matches,
            "settings": settings,
            "airports": get_airports_dict(),
            "version": get_version(),
        }
    )


@router.get("/api/trips")
async def list_trips(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    query = db.query(TripPlan).order_by(TripPlan.created_at.desc())
    if active_only:
        query = query.filter(TripPlan.is_active == True)
    
    trips = query.all()
    return {"trips": [TripPlanResponse.model_validate(t) for t in trips]}


@router.post("/api/trips")
async def create_trip(
    trip: TripPlanCreate,
    db: Session = Depends(get_db),
):
    invalid_origins = []
    for o in trip.origins:
        valid, error = AirportService.validate(o)
        if not valid:
            invalid_origins.append(f"{o}: {error}")
    if invalid_origins:
        raise HTTPException(status_code=400, detail=f"Invalid origin(s): {'; '.join(invalid_origins)}")
    
    invalid_dests = []
    for d in trip.destinations:
        valid, error = AirportService.validate(d)
        if not valid:
            invalid_dests.append(f"{d}: {error}")
    if invalid_dests:
        raise HTTPException(status_code=400, detail=f"Invalid destination(s): {'; '.join(invalid_dests)}")
    
    legs_data = [
        {"origin": leg.origin.upper(), "destination": leg.destination.upper(),
         "date_start": leg.date_start, "date_end": leg.date_end, "order": leg.order}
        for leg in trip.legs
    ]

    new_trip = TripPlan(
        name=trip.name,
        origins=[o.upper() for o in trip.origins],
        destinations=[d.upper() for d in trip.destinations],
        destination_types=trip.destination_types,
        legs=legs_data,
        available_from=trip.available_from,
        available_to=trip.available_to,
        trip_duration_min=trip.trip_duration_min,
        trip_duration_max=trip.trip_duration_max,
        budget_max=trip.budget_max,
        budget_currency=trip.budget_currency.upper(),
        cabin_classes=trip.cabin_classes,
        travelers_adults=trip.travelers_adults,
        travelers_children=trip.travelers_children,
        notify_on_match=trip.notify_on_match,
        check_frequency_hours=trip.check_frequency_hours,
        notes=trip.notes,
    )
    db.add(new_trip)
    db.commit()
    db.refresh(new_trip)
    
    matcher = TripMatcher(db)
    matcher.update_plan_matches(new_trip)
    
    return TripPlanResponse.model_validate(new_trip)


@router.get("/api/trips/{trip_id}")
async def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}
    return TripPlanResponse.model_validate(trip)


@router.get("/api/trips/{trip_id}/matches")
async def get_trip_matches(
    trip_id: int,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}
    
    matcher = TripMatcher(db)
    matches = matcher.get_matches_for_plan(trip_id, limit=limit)
    
    settings = UserSettings.get_or_create(db)
    preferred_currency = settings.preferred_currency or "NZD"
    
    return {
        "trip": TripPlanResponse.model_validate(trip),
        "matches": [
            {
                "deal": {
                    "id": deal.id,
                    "title": deal.raw_title,
                    "origin": deal.parsed_origin,
                    "destination": deal.parsed_destination,
                    "price": deal.parsed_price,
                    "currency": deal.parsed_currency,
                    "converted_price": CurrencyService.convert_sync(
                        deal.parsed_price, deal.parsed_currency or "USD", preferred_currency
                    ) if deal.parsed_price else None,
                    "preferred_currency": preferred_currency,
                    "airline": deal.parsed_airline,
                    "cabin_class": deal.parsed_cabin_class,
                    "source": deal.source.value,
                    "link": deal.link,
                    "published_at": deal.published_at.isoformat() if deal.published_at else None,
                },
                "match_score": score,
            }
            for deal, score in matches
        ],
    }


async def run_trip_search_background(trip_id: int):
    """Run trip search in background - survives client disconnect."""
    logger = logging.getLogger(__name__)
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
        if not trip:
            logger.error(f"Trip {trip_id} not found for background search")
            return
        
        search_service = TripPlanSearchService(db)
        try:
            summary = await search_service.search_trip_plan(trip_id)
            trip.search_in_progress = False
            trip.last_search_at = datetime.utcnow()
            db.commit()
            logger.info(f"Trip {trip_id} search completed: {summary.searches_successful}/{summary.searches_attempted} successful")
        except Exception as e:
            logger.error(f"Trip {trip_id} search failed: {e}")
            trip.search_in_progress = False
            db.commit()
        finally:
            await search_service.close()
    finally:
        db.close()


@router.post("/api/trips/{trip_id}/search")
async def search_trip_prices(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}
    
    now = datetime.utcnow()
    lock_timeout = timedelta(minutes=10)
    
    if trip.search_in_progress:
        if trip.search_started_at and (now - trip.search_started_at) < lock_timeout:
            return {
                "status": "already_searching",
                "message": "Search already in progress. Please wait for it to complete.",
                "started_at": trip.search_started_at.isoformat() if trip.search_started_at else None,
            }
        trip.search_in_progress = False
        db.commit()
    
    trip.search_in_progress = True
    trip.search_started_at = now
    db.commit()
    
    asyncio.create_task(run_trip_search_background(trip_id))
    
    return {
        "status": "started",
        "message": "Search started in background. Refresh the page to see results.",
        "trip_id": trip_id,
    }


@router.put("/api/trips/{trip_id}/toggle")
async def toggle_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}
    
    trip.is_active = not trip.is_active
    db.commit()
    
    return {"is_active": trip.is_active}


@router.put("/api/trips/{trip_id}")
async def update_trip(trip_id: int, trip_data: TripPlanCreate, db: Session = Depends(get_db)):
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    invalid_origins = []
    for o in trip_data.origins:
        valid, error = AirportService.validate(o)
        if not valid:
            invalid_origins.append(f"{o}: {error}")
    if invalid_origins:
        raise HTTPException(status_code=400, detail=f"Invalid origin(s): {'; '.join(invalid_origins)}")
    
    invalid_dests = []
    for d in trip_data.destinations:
        valid, error = AirportService.validate(d)
        if not valid:
            invalid_dests.append(f"{d}: {error}")
    if invalid_dests:
        raise HTTPException(status_code=400, detail=f"Invalid destination(s): {'; '.join(invalid_dests)}")
    
    trip.name = trip_data.name
    trip.origins = [o.upper() for o in trip_data.origins]
    trip.destinations = [d.upper() for d in trip_data.destinations]
    trip.destination_types = trip_data.destination_types
    trip.legs = [
        {"origin": leg.origin.upper(), "destination": leg.destination.upper(),
         "date_start": leg.date_start, "date_end": leg.date_end, "order": leg.order}
        for leg in trip_data.legs
    ]
    trip.available_from = trip_data.available_from
    trip.available_to = trip_data.available_to
    trip.trip_duration_min = trip_data.trip_duration_min
    trip.trip_duration_max = trip_data.trip_duration_max
    trip.budget_max = trip_data.budget_max
    trip.budget_currency = trip_data.budget_currency.upper()
    trip.travelers_adults = trip_data.travelers_adults
    trip.travelers_children = trip_data.travelers_children
    trip.check_frequency_hours = trip_data.check_frequency_hours
    
    db.commit()
    db.refresh(trip)
    
    matcher = TripMatcher(db)
    matcher.update_plan_matches(trip)
    
    return TripPlanResponse.model_validate(trip)


@router.delete("/api/trips/{trip_id}")
async def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}
    
    db.delete(trip)
    db.commit()
    
    return {"deleted": True}


@router.post("/api/trips/{trip_id}/check-matches")
async def check_trip_matches(trip_id: int, db: Session = Depends(get_db)):
    """
    Manually trigger match checking for a trip plan.
    Returns the number of matches found and top matches.
    """
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}
    
    matcher = TripMatcher(db)
    match_count = matcher.update_plan_matches(trip)
    matches = matcher.get_matches_for_plan(trip_id, limit=5)
    
    settings = UserSettings.get_or_create(db)
    preferred_currency = settings.preferred_currency or "NZD"
    
    return {
        "match_count": match_count,
        "last_match_at": trip.last_match_at.isoformat() if trip.last_match_at else None,
        "top_matches": [
            {
                "destination": deal.parsed_destination,
                "destination_city": airports.get(deal.parsed_destination, {}).get("city", deal.parsed_destination) if deal.parsed_destination else "Unknown",
                "price": deal.parsed_price,
                "currency": deal.parsed_currency,
                "converted_price": CurrencyService.convert_sync(
                    deal.parsed_price, deal.parsed_currency or "USD", preferred_currency
                ) if deal.parsed_price else None,
                "preferred_currency": preferred_currency,
                "airline": deal.parsed_airline,
                "source": deal.source.value,
                "link": deal.link,
                "score": score,
            }
            for deal, score in matches
        ],
    }
