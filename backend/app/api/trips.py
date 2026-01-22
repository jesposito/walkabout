from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os

from app.database import get_db
from app.models.trip_plan import TripPlan
from app.models.user_settings import UserSettings
from app.services.trip_matcher import TripMatcher
from app.services.currency import CurrencyService

router = APIRouter()

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)


class TripPlanCreate(BaseModel):
    name: str
    origins: list[str] = []
    destinations: list[str] = []
    destination_types: list[str] = []
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
    match_count: int
    last_match_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/", response_class=HTMLResponse)
async def trips_page(request: Request, db: Session = Depends(get_db)):
    trips = db.query(TripPlan).order_by(TripPlan.created_at.desc()).all()
    settings = UserSettings.get_or_create(db)
    
    trips_with_matches = []
    matcher = TripMatcher(db)
    for trip in trips:
        matches = matcher.get_matches_for_plan(trip.id, limit=5)
        trips_with_matches.append({
            "trip": trip,
            "top_matches": matches,
        })
    
    return templates.TemplateResponse(
        "trips.html",
        {
            "request": request,
            "trips": trips_with_matches,
            "settings": settings,
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
    new_trip = TripPlan(
        name=trip.name,
        origins=[o.upper() for o in trip.origins],
        destinations=[d.upper() for d in trip.destinations],
        destination_types=trip.destination_types,
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


@router.put("/api/trips/{trip_id}/toggle")
async def toggle_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}
    
    trip.is_active = not trip.is_active
    db.commit()
    
    return {"is_active": trip.is_active}


@router.delete("/api/trips/{trip_id}")
async def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(TripPlan).filter(TripPlan.id == trip_id).first()
    if not trip:
        return {"error": "Trip not found"}
    
    db.delete(trip)
    db.commit()
    
    return {"deleted": True}
