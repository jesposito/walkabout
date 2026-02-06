from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user_settings import UserSettings
from app.models import SearchDefinition, ScrapeHealth, FlightPrice
from app.scheduler import get_scheduler_status, manual_scrape_definition
from app.services.notification import NtfyNotifier
from app.services.scraping_service import ScrapingService
from app.config import get_settings
from app.utils.version import get_version

settings = get_settings()
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/legacy", response_class=HTMLResponse)
async def status_page(request: Request, db: Session = Depends(get_db)):
    """
    Main status page for Phase 1a - server-rendered HTML.
    
    Shows:
    - System status (scheduler, ntfy)
    - All search definitions with health
    - Quick action buttons
    """
    # Get scheduler status
    scheduler_status = get_scheduler_status()
    
    # Get all search definitions with their health
    search_definitions = db.query(SearchDefinition).filter(
        SearchDefinition.is_active == True
    ).all()
    
    # Enhance search definitions with health data and recent prices
    # Use a separate dict to store computed health data to avoid SQLAlchemy issues
    health_data = {}
    for search_def in search_definitions:
        health = search_def.scrape_health
        if health:
            recent_count = db.query(FlightPrice).filter(
                FlightPrice.search_definition_id == search_def.id,
                FlightPrice.scraped_at >= datetime.utcnow() - timedelta(days=7)
            ).count()
            health_data[search_def.id] = {
                'total_attempts': health.total_attempts,
                'total_successes': health.total_successes,
                'total_failures': health.total_failures,
                'consecutive_failures': health.consecutive_failures,
                'success_rate': health.success_rate,
                'healthy': health.is_healthy,
                'last_success_at': health.last_success_at,
                'last_failure_reason': health.last_failure_reason,
                'recent_prices_count': recent_count,
                'has_data': True,
            }
        else:
            health_data[search_def.id] = {
                'total_attempts': 0,
                'total_successes': 0,
                'total_failures': 0,
                'consecutive_failures': 0,
                'success_rate': 0,
                'healthy': True,
                'last_success_at': None,
                'last_failure_reason': None,
                'recent_prices_count': 0,
                'has_data': False,
            }
    
    # Get total prices across all search definitions
    total_prices = db.query(FlightPrice).count()
    
    # Test ntfy connectivity
    notifier = NtfyNotifier()
    try:
        ntfy_working = await notifier.send_test_notification()
    except:
        ntfy_working = False
    
    template_vars = {
        "request": request,
        "search_definitions": search_definitions,
        "health_data": health_data,
        "scheduler": scheduler_status,
        "total_prices": total_prices,
        "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ntfy_working": ntfy_working,
        "ntfy_url": settings.ntfy_url,
        "ntfy_topic": settings.ntfy_topic,
        "version": get_version(),
    }

    return templates.TemplateResponse("status.html", template_vars)


@router.post("/api/scrape/manual/all")
async def manual_scrape_all(db: Session = Depends(get_db)):
    """Manually trigger scraping for all active search definitions."""
    active_definitions = db.query(SearchDefinition).filter(
        SearchDefinition.is_active == True
    ).all()

    if not active_definitions:
        return {
            "success": True,
            "message": "No active search definitions to scrape",
            "successes": 0,
            "failures": 0,
            "errors": []
        }

    successes = 0
    failures = 0
    errors = []

    for search_def in active_definitions:
        try:
            result = await manual_scrape_definition(search_def.id)
            if result["success"]:
                successes += 1
            else:
                failures += 1
                errors.append({
                    "route": search_def.display_name,
                    "error": result.get("error", "Unknown error")
                })
        except Exception as e:
            failures += 1
            errors.append({
                "route": search_def.display_name,
                "error": str(e)
            })

    return {
        "success": successes > 0 or failures == 0,
        "message": f"Scraped {len(active_definitions)} definitions",
        "successes": successes,
        "failures": failures,
        "errors": errors
    }


@router.post("/api/scrape/manual/{search_definition_id}")
async def manual_scrape_single(search_definition_id: int, db: Session = Depends(get_db)):
    """Manually trigger a scrape for a specific search definition."""
    search_def = db.query(SearchDefinition).filter(
        SearchDefinition.id == search_definition_id
    ).first()

    if not search_def:
        raise HTTPException(status_code=404, detail="Search definition not found")

    try:
        result = await manual_scrape_definition(search_definition_id)

        if result["success"]:
            return {
                "success": True,
                "message": f"Found {result.get('prices_found', 0)} prices for {search_def.display_name}"
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "message": f"Scrape failed for {search_def.display_name}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/api/notifications/test")
async def test_notifications(db: Session = Depends(get_db)):
    """Send a test notification to verify ntfy is working."""
    from app.services.notification import get_global_notifier

    notifier = get_global_notifier()
    user_settings = UserSettings.get_or_create(db)

    try:
        success, message = await notifier.send_test_notification(user_settings=user_settings)
        return {
            "success": success,
            "message": message
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@router.get("/api/status/health")
async def health_check(db: Session = Depends(get_db)):
    """Simple health check endpoint for monitoring."""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Get basic stats
        active_definitions = db.query(SearchDefinition).filter(
            SearchDefinition.is_active == True
        ).count()
        
        # Get scheduler status
        scheduler = get_scheduler_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "scheduler": "running" if scheduler["running"] else "stopped",
            "active_monitors": active_definitions
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/search/{search_definition_id}/prices")
async def view_prices(search_definition_id: int, db: Session = Depends(get_db)):
    """Simple JSON view of recent prices for a search definition."""
    search_def = db.query(SearchDefinition).filter(
        SearchDefinition.id == search_definition_id
    ).first()
    
    if not search_def:
        raise HTTPException(status_code=404, detail="Search definition not found")
    
    # Get recent prices (last 30 days)
    prices = db.query(FlightPrice).filter(
        FlightPrice.search_definition_id == search_definition_id,
        FlightPrice.scraped_at >= datetime.utcnow() - timedelta(days=30)
    ).order_by(FlightPrice.scraped_at.desc()).limit(100).all()
    
    return {
        "search_definition": {
            "id": search_def.id,
            "name": search_def.display_name,
            "origin": search_def.origin,
            "destination": search_def.destination
        },
        "price_count": len(prices),
        "prices": [
            {
                "id": price.id,
                "scraped_at": price.scraped_at.isoformat(),
                "departure_date": price.departure_date.isoformat(),
                "return_date": price.return_date.isoformat() if price.return_date else None,
                "price_nzd": str(price.price_nzd),
                "airline": price.airline,
                "stops": price.stops
            }
            for price in prices
        ]
    }
