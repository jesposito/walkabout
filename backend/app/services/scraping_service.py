"""
Scraping orchestration service.

Coordinates scraping, health tracking, deal detection, and notifications.
"""

import hashlib
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import SearchDefinition, ScrapeHealth, FlightPrice
from app.models.user_settings import UserSettings
from app.scrapers.google_flights import GoogleFlightsScraper, ScrapeResult, FlightResult
from app.services.flight_price_fetcher import FlightPriceFetcher
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
        self.api_fetcher = FlightPriceFetcher(db=db)
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
                children=search_def.children,
                infants_in_seat=getattr(search_def, 'infants_in_seat', 0) or 0,
                infants_on_lap=getattr(search_def, 'infants_on_lap', 0) or 0,
                cabin_class=search_def.cabin_class.value if search_def.cabin_class else "economy",
                stops_filter=search_def.stops_filter.value if search_def.stops_filter else "any",
                currency=getattr(search_def, 'currency', 'USD') or 'USD',
                carry_on_bags=getattr(search_def, 'carry_on_bags', 0) or 0,
                checked_bags=getattr(search_def, 'checked_bags', 0) or 0,
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
    
    @staticmethod
    def _deterministic_sample(search_id: int, today: date, min_val: int, max_val: int) -> int:
        """Pick a deterministic value within [min_val, max_val] that varies by day.

        Uses a hash of (search_id, today) so the same search gets a consistent
        date within a single day, but samples different dates across days.
        """
        seed = hashlib.md5(f"{search_id}-{today.isoformat()}".encode()).hexdigest()
        hash_int = int(seed[:8], 16)
        return min_val + (hash_int % (max_val - min_val + 1))

    def _generate_travel_dates(self, search_def: SearchDefinition) -> tuple[date, Optional[date]]:
        """Generate travel dates for a scrape, sampling across the search window.

        Fixed-date searches use the start date directly. Rolling-window searches
        pick a different date each day (deterministic per search+day) to build
        price coverage across the entire window over time.
        """
        today = date.today()

        if search_def.departure_date_start and search_def.departure_date_end:
            # Fixed date mode - use the start date
            departure_date = search_def.departure_date_start
        else:
            # Rolling window mode - sample across the range
            if search_def.departure_days_min is not None:
                days_from_now = self._deterministic_sample(
                    search_def.id, today,
                    search_def.departure_days_min,
                    search_def.departure_days_max,
                )
                departure_date = today + timedelta(days=days_from_now)
            else:
                # Fallback - 60 days from now
                departure_date = today + timedelta(days=60)

        # Generate return date
        if search_def.trip_type.value == "one_way":
            return_date = None
        else:
            if search_def.trip_duration_days_min is not None:
                trip_days = self._deterministic_sample(
                    search_def.id + 10000, today,
                    search_def.trip_duration_days_min,
                    search_def.trip_duration_days_max,
                )
                return_date = departure_date + timedelta(days=trip_days)
            else:
                # Fallback - 7 day trip
                return_date = departure_date + timedelta(days=7)

        return departure_date, return_date
    
    # Confidence thresholds for data quality gating
    MIN_CONFIDENCE_FOR_STORAGE = 0.5
    MIN_CONFIDENCE_FOR_DEALS = 0.6

    async def _process_prices(
        self,
        search_def: SearchDefinition,
        flight_results: List,
        departure_date: date,
        return_date: Optional[date]
    ):
        """
        Process scraped prices: filter by confidence, store in DB, analyze for deals.

        Confidence gate:
        - Flights below MIN_CONFIDENCE_FOR_STORAGE (0.5) are logged but not stored
        - Flights below MIN_CONFIDENCE_FOR_DEALS (0.6) are stored but excluded from deal analysis
        """
        deals_found = []

        # Separate flights by confidence
        storable = []
        rejected = []
        for result in flight_results:
            confidence = result.raw_data.get("overall_confidence", 1.0) if result.raw_data else 1.0
            method = result.raw_data.get("extraction_method", "unknown") if result.raw_data else "unknown"

            if confidence < self.MIN_CONFIDENCE_FOR_STORAGE:
                rejected.append((result, confidence, method))
            else:
                storable.append((result, confidence, method))

        # Log rejected flights for debugging
        if rejected:
            logger.info(
                f"Confidence gate: rejected {len(rejected)} flights below "
                f"{self.MIN_CONFIDENCE_FOR_STORAGE} threshold "
                f"(prices: {[r[0].price_nzd for r in rejected]})"
            )

        # Log extraction method distribution
        per_row_count = sum(1 for _, _, m in storable if m == "per_row")
        page_level_count = sum(1 for _, _, m in storable if m == "page_level")
        if storable:
            avg_confidence = sum(c for _, c, _ in storable) / len(storable)
            logger.info(
                f"Storing {len(storable)} flights "
                f"(per_row: {per_row_count}, page_level: {page_level_count}, "
                f"avg confidence: {avg_confidence:.2f})"
            )

        # Get 30-day price history for anomaly detection
        history = self.price_analyzer.get_price_history(search_def.id, days=30)
        median_price = None
        if len(history) >= 5:
            median_price = sorted(history)[len(history) // 2]

        threshold_pct = settings.price_anomaly_threshold_percent

        # Store flights that pass the storage threshold
        from datetime import datetime as _dt
        _year_values = {_dt.now().year - 1, _dt.now().year, _dt.now().year + 1}

        for flight_result, confidence, method in storable:
            # Determine if this price is suspicious
            price_val = float(flight_result.price_nzd)
            is_suspicious = False

            # Absolute guard: year values are never valid prices
            if int(price_val) in _year_values:
                is_suspicious = True
                logger.warning(
                    f"Anomaly guard: ${price_val:.0f} matches calendar year "
                    f"for {search_def.display_name}"
                )

            # Relative guard: compare against historical median
            if not is_suspicious and median_price is not None:
                if price_val > median_price * (1 + threshold_pct / 100):
                    is_suspicious = True
                    logger.warning(
                        f"Anomaly guard: ${price_val:.0f} is >{threshold_pct:.0f}% above "
                        f"30-day median ${median_price:.0f} for {search_def.display_name}"
                    )
                elif price_val < median_price * 0.2:
                    is_suspicious = True
                    logger.warning(
                        f"Anomaly guard: ${price_val:.0f} is >80% below "
                        f"30-day median ${median_price:.0f} for {search_def.display_name}"
                    )

            # Compute total price (Google Flights shows per-person prices)
            passenger_count = search_def.total_passengers
            per_person_price = float(flight_result.price_nzd)
            total_price = per_person_price * passenger_count

            # Extract layover airports from raw_data if available
            layover_airports = None
            if flight_result.raw_data and "layover_airports" in flight_result.raw_data:
                layover_airports = ",".join(flight_result.raw_data["layover_airports"])

            price = FlightPrice(
                search_definition_id=search_def.id,
                departure_date=departure_date,
                return_date=return_date,
                price_nzd=flight_result.price_nzd,
                total_price_nzd=total_price,
                passengers=passenger_count,
                trip_type=search_def.trip_type.value if search_def.trip_type else None,
                airline=flight_result.airline,
                stops=flight_result.stops,
                duration_minutes=flight_result.duration_minutes,
                layover_airports=layover_airports,
                raw_data=flight_result.raw_data,
                confidence=confidence,
                is_suspicious=is_suspicious,
            )
            self.db.add(price)

        self.db.commit()

        # For deal analysis, only consider flights above the deal threshold and not suspicious
        deal_candidates = [
            (r, c, m) for r, c, m in storable
            if c >= self.MIN_CONFIDENCE_FOR_DEALS
            and not self._is_suspicious(r, median_price, threshold_pct)
        ]

        if deal_candidates:
            best_price = min(deal_candidates, key=lambda x: x[0].price_nzd)
            flight_result, confidence, method = best_price

            # Find the corresponding FlightPrice record we just created
            price_record = self.db.query(FlightPrice).filter(
                FlightPrice.search_definition_id == search_def.id,
                FlightPrice.departure_date == departure_date,
                FlightPrice.price_nzd == flight_result.price_nzd
            ).order_by(FlightPrice.id.desc()).first()

            if price_record:
                analysis = self.price_analyzer.analyze_price(price_record)

                if analysis.is_deal:
                    logger.info(
                        f"Deal detected: {search_def.display_name} - "
                        f"${flight_result.price_nzd} ({analysis.reason}) "
                        f"[confidence: {confidence:.2f}, method: {method}]"
                    )

                    user_settings = UserSettings.get_or_create(self.db)

                    await self.notifier.send_deal_alert(
                        search_def=search_def,
                        price=price_record,
                        analysis=analysis,
                        user_settings=user_settings,
                    )

                    deals_found.append(analysis)

        if deals_found:
            logger.info(f"Processed {len(flight_results)} prices, found {len(deals_found)} deals")
        else:
            logger.info(f"Processed {len(flight_results)} prices, no deals")
    
    @staticmethod
    def _is_suspicious(flight_result, median_price: float | None, threshold_pct: float) -> bool:
        if median_price is None:
            return False
        price_val = float(flight_result.price_nzd)
        if price_val > median_price * (1 + threshold_pct / 100):
            return True
        if price_val < median_price * 0.2:
            return True
        return False

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