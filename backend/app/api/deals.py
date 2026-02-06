from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.database import get_db
from app.services.feeds import FeedService
from app.services.relevance import RelevanceService, MAJOR_HUBS
from app.services.deal_rating import rate_unrated_deals
from app.services.currency import CurrencyService, convert_deal_price
from app.models.deal import DealSource
from app.models.user_settings import UserSettings
from app.utils.template_helpers import get_airports_dict
from app.utils.version import get_version

router = APIRouter()

template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=template_dir)


@router.get("/legacy", response_class=HTMLResponse)
async def deals_page(
    request: Request,
    source: Optional[str] = Query(None),
    cabin: Optional[str] = Query(None),
    tab: Optional[str] = Query("local"),
    sort: Optional[str] = Query("rating"),
    db: Session = Depends(get_db),
):
    service = FeedService(db)
    relevance_service = RelevanceService(db)
    settings = UserSettings.get_or_create(db)
    preferred_currency = settings.preferred_currency or "NZD"
    
    local_deals = relevance_service.get_local_deals(limit=100)
    regional_deals = relevance_service.get_regional_deals(limit=100)
    hub_deals = relevance_service.get_hub_deals(limit=100)
    
    if source:
        local_deals = [d for d in local_deals if d.source.value == source]
        regional_deals = [d for d in regional_deals if d.source.value == source]
        hub_deals = [d for d in hub_deals if d.source.value == source]
    if cabin:
        local_deals = [d for d in local_deals if d.parsed_cabin_class == cabin]
        regional_deals = [d for d in regional_deals if d.parsed_cabin_class == cabin]
        hub_deals = [d for d in hub_deals if d.parsed_cabin_class == cabin]
    
    def enrich_deal(deal):
        """Add converted price info to deal for template."""
        deal.price_info = convert_deal_price(
            deal.parsed_price,
            deal.parsed_currency or "USD",
            preferred_currency
        )
        return deal
    
    local_deals = [enrich_deal(d) for d in local_deals]
    regional_deals = [enrich_deal(d) for d in regional_deals]
    hub_deals = [enrich_deal(d) for d in hub_deals]
    
    def sort_deals(deals, sort_key):
        if sort_key == "price":
            return sorted(deals, key=lambda d: (d.price_info.get("converted_amount") if d.price_info else None) or 999999)
        elif sort_key == "date":
            return sorted(deals, key=lambda d: (d.published_at or d.created_at), reverse=True)
        else:
            return sorted(deals, key=lambda d: (d.deal_rating or -999), reverse=True)
    
    local_deals = sort_deals(local_deals, sort)
    regional_deals = sort_deals(regional_deals, sort)
    hub_deals = sort_deals(hub_deals, sort)
    
    feed_health = service.get_feed_health()
    
    sources = [s.value for s in DealSource]
    cabins = ["economy", "premium_economy", "business", "first"]
    
    hub_counts = relevance_service.get_hub_counts()
    
    # Check if AI is configured for enhanced mode
    ai_enabled = settings.ai_provider and settings.ai_provider != "none" and settings.ai_api_key
    
    # Default to date sort in basic mode if rating sort requested
    effective_sort = sort
    if not ai_enabled and sort in ["rating", "score"]:
        effective_sort = "date"
    
    # Re-sort with effective sort if it changed
    if effective_sort != sort:
        local_deals = sort_deals(local_deals, effective_sort)
        regional_deals = sort_deals(regional_deals, effective_sort)
        hub_deals = sort_deals(hub_deals, effective_sort)
    
    return templates.TemplateResponse(
        "deals.html",
        {
            "request": request,
            "local_deals": local_deals,
            "regional_deals": regional_deals,
            "hub_deals": hub_deals,
            "feed_health": feed_health,
            "sources": sources,
            "cabins": cabins,
            "current_source": source,
            "current_cabin": cabin,
            "current_tab": tab,
            "current_sort": effective_sort or "date",
            "local_count": len(local_deals),
            "regional_count": len(regional_deals),
            "hub_count": len(hub_deals),
            "airports": get_airports_dict(),
            "hub_counts": hub_counts,
            "major_hubs": MAJOR_HUBS,
            "preferred_currency": preferred_currency,
            "ai_enabled": ai_enabled,
            "version": get_version(),
        }
    )


def _serialize_deal(d, preferred_currency: str = "NZD"):
    """Serialize a deal model to dict with optional currency conversion."""
    converted = None
    if d.parsed_price and d.parsed_currency and d.parsed_currency != preferred_currency:
        converted = CurrencyService.convert_sync(
            d.parsed_price, d.parsed_currency, preferred_currency
        )

    return {
        "id": d.id,
        "title": d.raw_title,
        "origin": d.parsed_origin,
        "destination": d.parsed_destination,
        "price": d.parsed_price,
        "currency": d.parsed_currency,
        "converted_price": converted,
        "preferred_currency": preferred_currency,
        "airline": d.parsed_airline,
        "cabin_class": d.parsed_cabin_class,
        "source": d.source.value,
        "link": d.link,
        "published_at": d.published_at.isoformat() if d.published_at else None,
        "is_relevant": d.is_relevant,
        "relevance_reason": d.relevance_reason,
        "deal_rating": d.deal_rating,
        "rating_label": d.rating_label,
    }


@router.get("/api/deals")
async def get_deals_api(
    origin: Optional[str] = Query(None),
    relevant: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    service = FeedService(db)
    settings = UserSettings.get_or_create(db)
    preferred_currency = settings.preferred_currency or "NZD"
    deals = service.get_deals(origin=origin, relevant_only=relevant if relevant is not None else False, limit=limit, offset=offset)

    return {
        "deals": [_serialize_deal(d, preferred_currency) for d in deals],
        "count": len(deals),
    }


@router.get("/api/deals/categorized")
async def get_categorized_deals(
    limit: int = Query(50, le=200),
    sort: Optional[str] = Query("date"),
    db: Session = Depends(get_db),
):
    """Return deals split into local, regional, and worldwide categories."""
    relevance_service = RelevanceService(db)
    settings = UserSettings.get_or_create(db)
    preferred_currency = settings.preferred_currency or "NZD"

    local = relevance_service.get_local_deals(limit=limit)
    regional = relevance_service.get_regional_deals(limit=limit)
    hub = relevance_service.get_hub_deals(limit=limit)

    def sort_deals(deals, sort_key):
        if sort_key == "price":
            return sorted(deals, key=lambda d: d.parsed_price or 999999)
        elif sort_key == "rating":
            return sorted(deals, key=lambda d: d.deal_rating or -999, reverse=True)
        return sorted(deals, key=lambda d: d.published_at or d.created_at, reverse=True)

    local = sort_deals(local, sort)
    regional = sort_deals(regional, sort)
    hub = sort_deals(hub, sort)

    return {
        "local": [_serialize_deal(d, preferred_currency) for d in local],
        "regional": [_serialize_deal(d, preferred_currency) for d in regional],
        "worldwide": [_serialize_deal(d, preferred_currency) for d in hub],
        "counts": {
            "local": len(local),
            "regional": len(regional),
            "worldwide": len(hub),
        },
        "preferred_currency": preferred_currency,
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
    service = RelevanceService(db)
    updated = service.update_all_deals()
    return {"updated": updated, "message": f"Updated relevance for {updated} deals"}


@router.post("/api/reparse-deals")
async def reparse_deals(
    limit: int = Query(500, le=2000),
    db: Session = Depends(get_db),
):
    """Re-parse all deals to fix routes with updated airport lookup."""
    from app.models.deal import Deal
    from app.services.airports import AirportLookup
    import re
    
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"
        "\U00002600-\U000026FF"
        "]+",
        flags=re.UNICODE
    )
    
    deals = db.query(Deal).order_by(Deal.created_at.desc()).limit(limit).all()
    updated = 0
    
    for deal in deals:
        clean_title = EMOJI_PATTERN.sub(' ', deal.raw_title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        origin, destination = AirportLookup.extract_route(clean_title)
        
        if origin != deal.parsed_origin or destination != deal.parsed_destination:
            deal.parsed_origin = origin
            deal.parsed_destination = destination
            deal.deal_rating = None
            deal.rating_label = None
            deal.market_price = None
            updated += 1
    
    db.commit()
    
    if updated > 0:
        service = RelevanceService(db)
        service.update_all_deals()
    
    return {"reparsed": updated, "total": len(deals), "message": f"Re-parsed {updated} deals with updated routes"}


@router.post("/api/rate-deals")
async def trigger_deal_rating(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    rated_count = await rate_unrated_deals(db, limit=limit)
    return {"rated": rated_count, "message": f"Rated {rated_count} deals"}


@router.post("/api/test-ai-parse")
async def test_ai_parse(
    title: str = Query(..., description="Deal title to parse"),
    db: Session = Depends(get_db),
):
    """Test AI parsing on a single deal title."""
    from app.services.ai_service import AIService, configure_ai_from_settings
    from app.models.user_settings import UserSettings
    
    settings = UserSettings.get_or_create(db)
    configured = configure_ai_from_settings(settings)
    
    if not configured:
        return {"error": "AI not configured. Go to Settings and select an AI provider."}
    
    result = await AIService.parse_deal(title)
    return {
        "input": title,
        "parsed": {
            "origin": result.origin,
            "destination": result.destination,
            "price": result.price,
            "currency": result.currency,
            "cabin_class": result.cabin_class,
            "confidence": result.confidence,
        },
        "raw_response": result.raw_response,
    }


@router.post("/api/ai-reparse-deals")
async def ai_reparse_deals(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Re-parse deals using AI for better route extraction."""
    from app.models.deal import Deal
    from app.services.ai_service import AIService, configure_ai_from_settings
    from app.models.user_settings import UserSettings
    import asyncio
    
    settings = UserSettings.get_or_create(db)
    configured = configure_ai_from_settings(settings)
    
    if not configured:
        return {"error": "AI not configured. Go to Settings and select an AI provider."}
    
    # Get deals that might benefit from AI parsing (no destination or suspicious origins)
    deals = db.query(Deal).filter(
        (Deal.parsed_destination == None) | 
        (Deal.parsed_destination == '') |
        (Deal.parsed_origin.in_(['STO', 'NON', None, '']))
    ).order_by(Deal.created_at.desc()).limit(limit).all()
    
    # If no bad deals, get recent ones to improve
    if not deals:
        deals = db.query(Deal).order_by(Deal.created_at.desc()).limit(limit).all()
    
    updated = 0
    errors = 0
    
    for deal in deals:
        try:
            result = await AIService.parse_deal(deal.raw_title)
            
            if result.destination and result.confidence and result.confidence >= 0.7:
                changed = False
                
                if result.origin and result.origin != deal.parsed_origin:
                    deal.parsed_origin = result.origin
                    changed = True
                
                if result.destination != deal.parsed_destination:
                    deal.parsed_destination = result.destination
                    changed = True
                
                if result.price and result.price != deal.parsed_price:
                    deal.parsed_price = result.price
                    changed = True
                
                if result.currency and result.currency != deal.parsed_currency:
                    deal.parsed_currency = result.currency
                    changed = True
                
                if result.cabin_class and result.cabin_class.upper() != deal.parsed_cabin_class:
                    deal.parsed_cabin_class = result.cabin_class.upper()
                    changed = True
                
                if changed:
                    # Clear old ratings so they get recalculated
                    deal.deal_rating = None
                    deal.rating_label = None
                    deal.market_price = None
                    updated += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.2)
            
        except Exception as e:
            errors += 1
            continue
    
    db.commit()
    
    # Update relevance after reparsing
    if updated > 0:
        relevance_service = RelevanceService(db)
        relevance_service.update_all_deals()
    
    return {
        "reparsed": updated,
        "errors": errors,
        "total": len(deals),
        "message": f"AI re-parsed {updated} deals ({errors} errors)"
    }


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


@router.post("/api/deals/{deal_id}/dismiss")
async def dismiss_deal(deal_id: int, db: Session = Depends(get_db)):
    """Dismiss a deal (mark as not relevant)."""
    from app.models.deal import Deal

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Deal not found")

    deal.is_relevant = False
    deal.relevance_reason = "Dismissed by user"
    db.commit()

    return {"success": True, "message": f"Deal {deal_id} dismissed"}


@router.post("/api/deals/{deal_id}/restore")
async def restore_deal(deal_id: int, db: Session = Depends(get_db)):
    """Restore a dismissed deal."""
    from app.models.deal import Deal

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Deal not found")

    deal.is_relevant = True
    deal.relevance_reason = "Restored by user"
    db.commit()

    return {"success": True, "message": f"Deal {deal_id} restored"}
