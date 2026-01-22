from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
import os

from app.database import get_db
from app.models.flight_price import FlightPrice
from app.models.search_definition import SearchDefinition, TripType, CabinClass, StopsFilter

router = APIRouter()

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)


class PriceResponse(BaseModel):
    id: int
    search_definition_id: int
    scraped_at: datetime
    departure_date: date
    return_date: Optional[date]
    price_nzd: Decimal
    airline: Optional[str]
    stops: int
    duration_minutes: Optional[int]
    
    class Config:
        from_attributes = True


class PriceStats(BaseModel):
    search_definition_id: int
    min_price: Optional[Decimal]
    max_price: Optional[Decimal]
    avg_price: Optional[Decimal]
    current_price: Optional[Decimal]
    price_count: int
    price_trend: Optional[str] = None


class SearchDefinitionResponse(BaseModel):
    id: int
    origin: str
    destination: str
    trip_type: str
    adults: int
    children: int
    cabin_class: str
    stops_filter: str
    currency: str
    name: Optional[str]
    is_active: bool
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class SearchDefinitionCreate(BaseModel):
    origin: str
    destination: str
    trip_type: str = "round_trip"
    adults: int = 2
    children: int = 2
    infants_in_seat: int = 0
    infants_on_lap: int = 0
    cabin_class: str = "economy"
    stops_filter: str = "any"
    currency: str = "NZD"
    name: Optional[str] = None
    departure_days_min: Optional[int] = 60
    departure_days_max: Optional[int] = 120
    trip_duration_days_min: Optional[int] = 7
    trip_duration_days_max: Optional[int] = 14


@router.get("/", response_class=HTMLResponse)
async def prices_page(request: Request, db: Session = Depends(get_db)):
    searches = db.query(SearchDefinition).filter(
        SearchDefinition.is_active == True
    ).order_by(SearchDefinition.created_at.desc()).all()
    return templates.TemplateResponse(
        "prices.html",
        {"request": request, "searches": searches}
    )


@router.get("/searches", response_model=list[SearchDefinitionResponse])
async def list_search_definitions(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    query = db.query(SearchDefinition)
    if active_only:
        query = query.filter(SearchDefinition.is_active == True)
    return query.order_by(SearchDefinition.created_at.desc()).all()


@router.post("/searches", response_model=SearchDefinitionResponse)
async def create_search_definition(
    search: SearchDefinitionCreate,
    db: Session = Depends(get_db),
):
    definition = SearchDefinition(
        origin=search.origin.upper(),
        destination=search.destination.upper(),
        trip_type=TripType(search.trip_type),
        adults=search.adults,
        children=search.children,
        infants_in_seat=search.infants_in_seat,
        infants_on_lap=search.infants_on_lap,
        cabin_class=CabinClass(search.cabin_class),
        stops_filter=StopsFilter(search.stops_filter),
        currency=search.currency.upper(),
        name=search.name,
        departure_days_min=search.departure_days_min,
        departure_days_max=search.departure_days_max,
        trip_duration_days_min=search.trip_duration_days_min,
        trip_duration_days_max=search.trip_duration_days_max,
    )
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return definition


@router.get("/searches/{search_id}", response_model=SearchDefinitionResponse)
async def get_search_definition(
    search_id: int,
    db: Session = Depends(get_db),
):
    definition = db.query(SearchDefinition).filter(SearchDefinition.id == search_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="Search definition not found")
    return definition


@router.delete("/searches/{search_id}")
async def delete_search_definition(
    search_id: int,
    db: Session = Depends(get_db),
):
    definition = db.query(SearchDefinition).filter(SearchDefinition.id == search_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="Search definition not found")
    
    definition.is_active = False
    db.commit()
    return {"status": "deactivated", "id": search_id}


@router.get("/searches/{search_id}/prices", response_model=list[PriceResponse])
async def get_price_history(
    search_id: int,
    days: int = Query(default=30, le=365),
    departure_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    definition = db.query(SearchDefinition).filter(SearchDefinition.id == search_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="Search definition not found")
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = db.query(FlightPrice).filter(
        FlightPrice.search_definition_id == search_id,
        FlightPrice.scraped_at >= cutoff,
    )
    
    if departure_date:
        query = query.filter(FlightPrice.departure_date == departure_date)
    
    return query.order_by(FlightPrice.scraped_at.desc()).limit(500).all()


@router.get("/searches/{search_id}/stats", response_model=PriceStats)
async def get_price_stats(
    search_id: int,
    days: int = Query(default=90, le=365),
    db: Session = Depends(get_db),
):
    definition = db.query(SearchDefinition).filter(SearchDefinition.id == search_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="Search definition not found")
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    stats = db.query(
        func.min(FlightPrice.price_nzd).label("min_price"),
        func.max(FlightPrice.price_nzd).label("max_price"),
        func.avg(FlightPrice.price_nzd).label("avg_price"),
        func.count(FlightPrice.id).label("price_count"),
    ).filter(
        FlightPrice.search_definition_id == search_id,
        FlightPrice.scraped_at >= cutoff,
    ).first()
    
    latest = db.query(FlightPrice).filter(
        FlightPrice.search_definition_id == search_id,
    ).order_by(FlightPrice.scraped_at.desc()).first()
    
    trend = None
    if stats.price_count and stats.price_count > 5 and latest and stats.avg_price:
        if float(latest.price_nzd) < float(stats.avg_price) * 0.9:
            trend = "down"
        elif float(latest.price_nzd) > float(stats.avg_price) * 1.1:
            trend = "up"
        else:
            trend = "stable"
    
    return PriceStats(
        search_definition_id=search_id,
        min_price=stats.min_price,
        max_price=stats.max_price,
        avg_price=stats.avg_price,
        current_price=Decimal(str(latest.price_nzd)) if latest else None,
        price_count=stats.price_count or 0,
        price_trend=trend,
    )


@router.get("/searches/{search_id}/latest", response_model=list[PriceResponse])
async def get_latest_prices(
    search_id: int,
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
):
    definition = db.query(SearchDefinition).filter(SearchDefinition.id == search_id).first()
    if not definition:
        raise HTTPException(status_code=404, detail="Search definition not found")
    
    return db.query(FlightPrice).filter(
        FlightPrice.search_definition_id == search_id,
    ).order_by(FlightPrice.scraped_at.desc()).limit(limit).all()
