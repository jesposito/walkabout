from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, timedelta
from app.database import get_db
from app.models import FlightPrice, Route
from app.schemas import FlightPriceResponse, PriceStats

router = APIRouter()


@router.get("/{route_id}", response_model=List[FlightPriceResponse])
async def get_price_history(
    route_id: int,
    days: int = Query(default=30, le=365),
    departure_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    query = db.query(FlightPrice).filter(
        FlightPrice.route_id == route_id,
        FlightPrice.scraped_at >= func.now() - timedelta(days=days)
    )
    
    if departure_date:
        query = query.filter(FlightPrice.departure_date == departure_date)
    
    return query.order_by(FlightPrice.scraped_at.desc()).limit(500).all()


@router.get("/{route_id}/latest", response_model=List[FlightPriceResponse])
async def get_latest_prices(
    route_id: int,
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    return db.query(FlightPrice).filter(
        FlightPrice.route_id == route_id
    ).order_by(FlightPrice.scraped_at.desc()).limit(limit).all()


@router.get("/{route_id}/stats", response_model=PriceStats)
async def get_price_stats(
    route_id: int,
    days: int = Query(default=90, le=365),
    db: Session = Depends(get_db)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    stats = db.query(
        func.min(FlightPrice.price_nzd).label("min_price"),
        func.max(FlightPrice.price_nzd).label("max_price"),
        func.avg(FlightPrice.price_nzd).label("avg_price"),
        func.count(FlightPrice.id).label("price_count")
    ).filter(
        FlightPrice.route_id == route_id,
        FlightPrice.scraped_at >= func.now() - timedelta(days=days)
    ).first()
    
    latest = db.query(FlightPrice).filter(
        FlightPrice.route_id == route_id
    ).order_by(FlightPrice.scraped_at.desc()).first()
    
    return PriceStats(
        route_id=route_id,
        min_price=stats.min_price or 0,
        max_price=stats.max_price or 0,
        avg_price=stats.avg_price or 0,
        current_price=latest.price_nzd if latest else None,
        price_count=stats.price_count or 0
    )
