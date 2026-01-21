"""
Scraping orchestration service for Phase 1a.

Coordinates scraping, health tracking, deal detection, and notifications.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import SearchDefinition, ScrapeHealth, FlightPrice
from app.scrapers.google_flights import GoogleFlightsScraper, ScrapeResult
from app.services.price_analyzer import PriceAnalyzer
from app.services.notification import NtfyNotifier
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScrapingService:
    """
    Orchestrates the entire scraping pipeline:
    1. Execute scrape
    2. Update health tracking
    3. Store prices
    4. Analyze for deals
    5. Send notifications
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.scraper = GoogleFlightsScraper()
        self.price_analyzer = PriceAnalyzer(db)
        self.notifier = NtfyNotifier()
    
    async def scrape_search_definition(self, search_definition_id: int) -> ScrapeResult:
        """
        Scrape a search definition and handle all the orchestration.
        
        Returns: ScrapeResult with status and prices
        """
        search_def = self.db.query(SearchDefinition).filter(
            SearchDefinition.id == search_definition_id
        ).first()
        
        if not search_def:
            raise ValueError(f"SearchDefinition {search_definition_id} not found")
        
        # Get or create health record
        health = search_def.scrape_health
        if not health:
            health = ScrapeHealth(search_definition_id=search_definition_id)
            self.db.add(health)
            self.db.commit()
            search_def.scrape_health = health
        
        # Check circuit breaker
        if health.circuit_open:
            logger.warning(f"Circuit breaker open for {search_def.display_name}, skipping scrape")
            return ScrapeResult(
                status="blocked",
                error_message="Circuit breaker is open - too many consecutive failures"
            )
        
        # Generate travel dates for this scrape
        departure_date, return_date = self._generate_travel_dates(search_def)
        
        logger.info(f"Scraping {search_def.display_name}: {departure_date} -> {return_date}")
        
        # Execute the scrape
        try:
            result = await self.scraper.scrape_route(
                search_definition_id=search_def.id,
                origin=search_def.origin,
                destination=search_def.destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=search_def.adults,
                children=search_def.children
            )
        except Exception as e:
            logger.error(f"Scraper exception for {search_def.display_name}: {e}")
            result = ScrapeResult(
                status="unknown",
                error_message=f"Scraper exception: {str(e)}"
            )
        
        # Update health tracking
        if result.is_success:
            health.record_success()
            logger.info(f"Scrape success: {search_def.display_name} - {len(result.prices)} prices")
        else:
            health.record_failure(
                reason=result.status,
                message=result.error_message,
                screenshot_path=result.screenshot_path,
                html_snapshot_path=result.html_snapshot_path
            )
            logger.error(f"Scrape failed: {search_def.display_name} - {result.status}")
        
        self.db.commit()
        
        # If successful, process the prices
        if result.is_success and result.prices:
            await self._process_prices(search_def, result.prices, departure_date, return_date)
        
        return result
    
    def _generate_travel_dates(self, search_def: SearchDefinition) -> tuple[date, Optional[date]]:
        """
        Generate specific travel dates based on the search definition pattern.
        
        For Phase 1a, we'll use the simplest approach: middle of the window.
        """
        if search_def.departure_date_start and search_def.departure_date_end:
            # Fixed date mode - use the start date
            departure_date = search_def.departure_date_start
        else:
            # Rolling window mode - pick middle of range
            if search_def.departure_days_min is not None:
                days_from_now = (search_def.departure_days_min + search_def.departure_days_max) // 2
                departure_date = date.today() + timedelta(days=days_from_now)
            else:
                # Fallback - 60 days from now
                departure_date = date.today() + timedelta(days=60)
        
        # Generate return date
        if search_def.trip_type.value == "one_way":
            return_date = None
        else:
            if search_def.trip_duration_days_min is not None:
                trip_days = (search_def.trip_duration_days_min + search_def.trip_duration_days_max) // 2
                return_date = departure_date + timedelta(days=trip_days)
            else:
                # Fallback - 7 day trip
                return_date = departure_date + timedelta(days=7)
        
        return departure_date, return_date
    
    async def _process_prices(
        self,
        search_def: SearchDefinition,
        flight_results: List,
        departure_date: date,
        return_date: Optional[date]
    ):
        """
        Process scraped prices: store in DB, analyze for deals, send notifications.
        """
        deals_found = []
        
        for flight_result in flight_results:
            # Store the price
            price = FlightPrice(
                search_definition_id=search_def.id,
                departure_date=departure_date,
                return_date=return_date,
                price_nzd=flight_result.price_nzd,
                airline=flight_result.airline,
                stops=flight_result.stops,
                duration_minutes=flight_result.duration_minutes,
                raw_data=flight_result.raw_data
            )
            self.db.add(price)
        
        self.db.commit()
        
        # For simplicity in Phase 1a, analyze just the best (cheapest) price
        if flight_results:
            best_price = min(flight_results, key=lambda x: x.price_nzd)
            
            # Find the corresponding FlightPrice record we just created
            price_record = self.db.query(FlightPrice).filter(
                FlightPrice.search_definition_id == search_def.id,
                FlightPrice.departure_date == departure_date,
                FlightPrice.price_nzd == best_price.price_nzd
            ).order_by(FlightPrice.id.desc()).first()
            
            if price_record:
                # Analyze for deals
                analysis = self.price_analyzer.analyze_price(price_record)
                
                if analysis.is_deal:
                    logger.info(f"🎉 Deal detected: {search_def.display_name} - ${best_price.price_nzd} ({analysis.reason})")
                    
                    # Send notification
                    await self.notifier.send_deal_alert(
                        search_def=search_def,
                        price=price_record,
                        analysis=analysis
                    )
                    
                    deals_found.append(analysis)
        
        if deals_found:
            logger.info(f"Processed {len(flight_results)} prices, found {len(deals_found)} deals")
        else:
            logger.info(f"Processed {len(flight_results)} prices, no deals")
    
    async def send_stale_data_alert(self, search_def: SearchDefinition, health: ScrapeHealth):
        """Send alert for stale data (no successful scrape for too long)."""
        hours_since_success = (datetime.utcnow() - health.last_success_at).total_seconds() / 3600
        
        await self.notifier.send_system_alert(
            title=f"⚠️ Stale Data: {search_def.display_name}",
            message=f"No successful scrape for {hours_since_success:.1f} hours.\n"
                   f"Last success: {health.last_success_at}\n"
                   f"Consecutive failures: {health.consecutive_failures}",
            priority="default"
        )
    
    async def send_failure_alert(self, search_def: SearchDefinition, health: ScrapeHealth):
        """Send alert for consecutive scrape failures."""
        await self.notifier.send_system_alert(
            title=f"🚨 Scraping Failures: {search_def.display_name}",
            message=f"{health.consecutive_failures} consecutive failures.\n"
                   f"Last error: {health.last_failure_reason}\n"
                   f"Message: {health.last_failure_message or 'N/A'}",
            priority="high"
        )
    
    def get_scrape_status(self, search_definition_id: int) -> dict:
        """Get current scrape status for a search definition."""
        search_def = self.db.query(SearchDefinition).filter(
            SearchDefinition.id == search_definition_id
        ).first()
        
        if not search_def:
            return {"error": "Search definition not found"}
        
        health = search_def.scrape_health
        
        if not health:
            return {
                "search_definition": search_def.display_name,
                "status": "never_scraped",
                "healthy": True,
                "total_attempts": 0
            }
        
        # Get recent prices count
        recent_prices_count = self.db.query(FlightPrice).filter(
            FlightPrice.search_definition_id == search_definition_id,
            FlightPrice.scraped_at >= datetime.utcnow() - timedelta(days=7)
        ).count()
        
        return {
            "search_definition": search_def.display_name,
            "status": "healthy" if health.is_healthy else "unhealthy",
            "healthy": health.is_healthy,
            "total_attempts": health.total_attempts,
            "total_successes": health.total_successes,
            "total_failures": health.total_failures,
            "consecutive_failures": health.consecutive_failures,
            "success_rate": health.success_rate,
            "last_attempt_at": health.last_attempt_at.isoformat() if health.last_attempt_at else None,
            "last_success_at": health.last_success_at.isoformat() if health.last_success_at else None,
            "last_failure_reason": health.last_failure_reason,
            "circuit_open": bool(health.circuit_open),
            "recent_prices_count": recent_prices_count
        }