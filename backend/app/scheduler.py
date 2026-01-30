"""
APScheduler setup for Phase 1a - Simple scheduling without Celery complexity.

Oracle Review: "Consider defer Celery/Redis initially. A single cron/APScheduler 
can run 2-6 jobs/day safely."
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import SearchDefinition, ScrapeHealth, TripPlan
from app.services.scraping_service import ScrapingService
from app.services.trip_plan_search import TripPlanSearchService
from app.services.deal_rating import rate_unrated_deals
from app.config import get_settings
import os

# Configure logging
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

settings = get_settings()


def get_scheduler() -> AsyncIOScheduler:
    """Get or create the global scheduler instance."""
    global scheduler
    if scheduler is None:
        # Get timezone from TZ environment variable, default to UTC
        tz = os.environ.get('TZ', 'UTC')
        logger.info(f"Scheduler using timezone: {tz}")

        # Create scheduler with memory jobstore (simple for Phase 1a)
        scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            timezone=tz
        )

        # Add scheduled jobs
        _setup_scheduled_jobs()

    return scheduler


def _setup_scheduled_jobs():
    """Setup the scheduled scraping jobs."""
    
    # Morning scrape (6:30 AM local time)
    scheduler.add_job(
        scrape_all_active_definitions,
        trigger=CronTrigger(hour=6, minute=30),
        id='morning_scrape',
        name='Morning Scrape (6:30 AM)',
        replace_existing=True,
        max_instances=1,
    )

    # Evening scrape (6:30 PM local time)
    scheduler.add_job(
        scrape_all_active_definitions,
        trigger=CronTrigger(hour=18, minute=30),
        id='evening_scrape',
        name='Evening Scrape (6:30 PM)',
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.add_job(
        check_scrape_health,
        trigger=IntervalTrigger(hours=1),
        id='health_check',
        name='Scrape Health Check',
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.add_job(
        search_active_trip_plans,
        trigger=IntervalTrigger(hours=6),
        id='trip_plan_search',
        name='Trip Plan Google Flights Search',
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.add_job(
        rate_deals_job,
        trigger=IntervalTrigger(hours=2),
        id='deal_rating',
        name='Rate Unrated Deals',
        replace_existing=True,
        max_instances=1,
    )
    
    logger.info("Scheduled jobs configured:")
    logger.info("  - Morning scrape: 6:30 AM daily (local time)")
    logger.info("  - Evening scrape: 6:30 PM daily (local time)")
    logger.info("  - Health check: Every hour")
    logger.info("  - Trip Plan search: Every 6 hours")
    logger.info("  - Deal rating: Every 2 hours")


async def scrape_all_active_definitions():
    """
    Scrape all active search definitions.
    
    This is the main job that runs 2x daily.
    """
    logger.info("Starting scheduled scrape of all active definitions")
    
    db = SessionLocal()
    scraping_service = ScrapingService(db)
    
    try:
        # Get all active search definitions
        active_definitions = db.query(SearchDefinition).filter(
            SearchDefinition.is_active == True
        ).all()
        
        if not active_definitions:
            logger.warning("No active search definitions found")
            return
        
        logger.info(f"Found {len(active_definitions)} active search definitions")
        
        # Scrape each definition
        total_successes = 0
        total_failures = 0
        
        for search_def in active_definitions:
            try:
                logger.info(f"Scraping: {search_def.display_name}")
                
                result = await scraping_service.scrape_search_definition(search_def.id)
                
                if result.is_success:
                    total_successes += 1
                    logger.info(f"✅ Success: {search_def.display_name} - {len(result.prices)} prices")
                else:
                    total_failures += 1
                    logger.error(f"❌ Failed: {search_def.display_name} - {result.status}: {result.error_message}")
                
            except Exception as e:
                total_failures += 1
                logger.error(f"❌ Exception scraping {search_def.display_name}: {e}")
        
        logger.info(f"Scheduled scrape complete: {total_successes} successes, {total_failures} failures")
        
    except Exception as e:
        logger.error(f"Error in scheduled scrape: {e}")
        
    finally:
        db.close()


async def check_scrape_health():
    """
    Check scrape health and send alerts for stale data or consecutive failures.
    
    Oracle Review: "Alert on stale data (no successful scrape for X hours)"
    """
    logger.debug("Running scrape health check")
    
    db = SessionLocal()
    scraping_service = ScrapingService(db)
    
    try:
        # Get all search definitions with their health
        search_definitions = db.query(SearchDefinition).filter(
            SearchDefinition.is_active == True
        ).all()
        
        for search_def in search_definitions:
            health = search_def.scrape_health
            if not health:
                continue  # No scraping attempted yet
                
            # Check for stale data (no success in last 25 hours)
            if health.last_success_at:
                hours_since_success = (datetime.utcnow() - health.last_success_at).total_seconds() / 3600
                
                if hours_since_success > 25:  # More than a day + buffer
                    # Check if we've already sent an alert recently
                    if (not health.stale_alert_sent_at or 
                        (datetime.utcnow() - health.stale_alert_sent_at).total_seconds() > 86400):  # 24h
                        
                        await scraping_service.send_stale_data_alert(search_def, health)
                        
                        # Update alert timestamp
                        health.stale_alert_sent_at = datetime.utcnow()
                        db.commit()
            
            # Check for consecutive failures
            if health.consecutive_failures >= 3 and not health.circuit_open:
                await scraping_service.send_failure_alert(search_def, health)
        
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        
    finally:
        db.close()


async def rate_deals_job():
    """Rate unrated deals by fetching market prices."""
    logger.info("Starting scheduled deal rating job")
    
    db = SessionLocal()
    
    try:
        rated_count = await rate_unrated_deals(db, limit=10)
        logger.info(f"Deal rating complete: {rated_count} deals rated")
    except Exception as e:
        logger.error(f"Error in deal rating job: {e}")
    finally:
        db.close()


async def search_active_trip_plans():
    """Search Google Flights for active Trip Plans that are due for a search."""
    logger.info("Starting scheduled Trip Plan searches")
    
    db = SessionLocal()
    
    try:
        active_plans = db.query(TripPlan).filter(
            TripPlan.is_active == True
        ).all()
        
        if not active_plans:
            logger.info("No active Trip Plans to search")
            return
        
        logger.info(f"Found {len(active_plans)} active Trip Plans")
        
        now = datetime.utcnow()
        searched = 0
        skipped = 0
        
        for plan in active_plans:
            hours_since_update = float('inf')
            if plan.updated_at:
                hours_since_update = (now - plan.updated_at).total_seconds() / 3600
            
            check_freq = plan.check_frequency_hours or 12
            
            if hours_since_update < check_freq:
                skipped += 1
                continue
            
            logger.info(f"Searching Trip Plan {plan.id}: {plan.name}")
            
            search_service = TripPlanSearchService(db)
            try:
                summary = await search_service.search_trip_plan(plan.id)
                
                if summary.searches_successful > 0:
                    logger.info(f"  Found {len(summary.results)} results for {plan.name}")
                else:
                    logger.warning(f"  No results for {plan.name}")
                
                searched += 1
                
            except Exception as e:
                logger.error(f"  Error searching {plan.name}: {e}")
            finally:
                await search_service.close()
        
        logger.info(f"Trip Plan search complete: {searched} searched, {skipped} skipped (not due)")
        
    except Exception as e:
        logger.error(f"Error in Trip Plan search job: {e}")
        
    finally:
        db.close()


async def manual_scrape_definition(search_definition_id: int) -> dict:
    """
    Manually trigger a scrape for a specific search definition.

    Returns: Dict with success status and error message if failed
    """
    logger.info(f"Manual scrape triggered for search definition {search_definition_id}")

    db = SessionLocal()
    scraping_service = ScrapingService(db)

    try:
        result = await scraping_service.scrape_search_definition(search_definition_id)

        if result.is_success:
            logger.info(f"✅ Manual scrape success: {len(result.prices)} prices")
            return {
                "success": True,
                "prices_found": len(result.prices)
            }
        else:
            logger.error(f"❌ Manual scrape failed: {result.status} - {result.error_message}")
            return {
                "success": False,
                "error": result.error_message or result.status,
                "status": result.status
            }

    except Exception as e:
        logger.error(f"Error in manual scrape: {e}")
        return {
            "success": False,
            "error": str(e),
            "status": "exception"
        }

    finally:
        db.close()


def start_scheduler():
    """Start the scheduler (call this from FastAPI startup)."""
    scheduler_instance = get_scheduler()
    
    if not scheduler_instance.running:
        scheduler_instance.start()
        logger.info("APScheduler started successfully")
        
        # Log next job times
        for job in scheduler_instance.get_jobs():
            next_run = job.next_run_time
            logger.info(f"Next '{job.name}': {next_run}")
    else:
        logger.warning("Scheduler already running")


def stop_scheduler():
    """Stop the scheduler (call this from FastAPI shutdown)."""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped")
        scheduler = None


def get_scheduler_status() -> dict:
    """Get scheduler status for the status page."""
    if scheduler is None or not scheduler.running:
        return {
            "running": False,
            "jobs": [],
            "next_run": None
        }
    
    jobs = []
    next_run = None
    
    for job in scheduler.get_jobs():
        job_data = {
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "func": job.func.__name__ if job.func else None
        }
        jobs.append(job_data)
        
        # Find earliest next run
        if job.next_run_time and (next_run is None or job.next_run_time < next_run):
            next_run = job.next_run_time
    
    return {
        "running": True,
        "jobs": jobs,
        "next_run": next_run.isoformat() if next_run else None
    }
