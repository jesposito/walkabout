from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.database import get_db
from app.services.feeds import FeedService
from app.services.relevance import RelevanceService, MAJOR_HUBS
from app.models.deal import DealSource
from app.utils.template_helpers import get_airports_dict

router = APIRouter()

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)


@router.get("/", response_class=HTMLResponse)
async def deals_page(
    request: Request,
    source: Optional[str] = Query(None),
    cabin: Optional[str] = Query(None),
    relevant: Optional[bool] = Query(True),
    sort: Optional[str] = Query("score"),
    db: Session = Depends(get_db),
):
    service = FeedService(db)
    relevance_service = RelevanceService(db)
    
    use_relevant = relevant if relevant is not None else True
    
    if use_relevant:
        deals = relevance_service.get_home_deals(limit=100)
    else:
        deals = service.get_deals(relevant_only=False, limit=100, sort_by=sort or "score")
    
    if source:
        deals = [d for d in deals if d.source.value == source]
    if cabin:
        deals = [d for d in deals if d.parsed_cabin_class == cabin]
    
    feed_health = service.get_feed_health()
    
    sources = [s.value for s in DealSource]
    cabins = ["economy", "premium_economy", "business", "first"]
    
    all_count = len(service.get_deals(relevant_only=False, limit=500))
    home_deals_count = len(relevance_service.get_home_deals(limit=500))
    
    hub_deals = relevance_service.get_hub_deals(limit=50)
    hub_counts = relevance_service.get_hub_counts()
    
    return templates.TemplateResponse(
        "deals.html",
        {
            "request": request,
            "deals": deals,
            "feed_health": feed_health,
            "sources": sources,
            "cabins": cabins,
            "current_source": source,
            "current_cabin": cabin,
            "current_relevant": relevant,
            "current_sort": sort or "score",
            "all_count": all_count,
            "relevant_count": home_deals_count,
            "airports": get_airports_dict(),
            "hub_deals": hub_deals,
            "hub_counts": hub_counts,
            "major_hubs": MAJOR_HUBS,
        }
    )


@router.get("/api/deals")
async def get_deals_api(
    origin: Optional[str] = Query(None),
    relevant: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    service = FeedService(db)
    deals = service.get_deals(origin=origin, relevant_only=relevant if relevant is not None else False, limit=limit, offset=offset)
    
    return {
        "deals": [
            {
                "id": d.id,
                "title": d.raw_title,
                "origin": d.parsed_origin,
                "destination": d.parsed_destination,
                "price": d.parsed_price,
                "currency": d.parsed_currency,
                "airline": d.parsed_airline,
                "cabin_class": d.parsed_cabin_class,
                "source": d.source.value,
                "link": d.link,
                "published_at": d.published_at.isoformat() if d.published_at else None,
                "is_relevant": d.is_relevant,
                "relevance_reason": d.relevance_reason,
            }
            for d in deals
        ],
        "count": len(deals),
    }


@router.get("/api/health/feeds")
async def get_feed_health(db: Session = Depends(get_db)):
    service = FeedService(db)
    return {"feeds": service.get_feed_health()}


@router.post("/api/ingest")
async def trigger_ingest(db: Session = Depends(get_db)):
    service = FeedService(db)
    results = await service.ingest_all_feeds()
    return {"results": results}


@router.post("/api/recalculate-relevance")
async def recalculate_relevance(db: Session = Depends(get_db)):
    """Recalculate relevance scores for all deals based on current settings."""
    service = RelevanceService(db)
    updated = service.update_all_deals()
    return {"updated": updated, "message": f"Updated relevance for {updated} deals"}


@router.get("/api/insights")
async def get_insights(
    home_airport: str = Query("AKL"),
    destinations: str = Query("SYD,NAN,HNL,TYO"),
    db: Session = Depends(get_db),
):
    service = FeedService(db)
    watched = [d.strip() for d in destinations.split(",")]
    insights = await service.get_insights(home_airport, watched)
    return insights
