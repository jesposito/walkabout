"""
Trip Plan Search Service - Active Google Flights searching for Trip Plans.

Unlike Routes (which search specific origin-destination pairs), Trip Plans
support flexible searching with:
- Multiple possible origins
- Multiple possible destinations (or destination types like "japan")
- Date ranges
- Budget constraints

This service expands Trip Plan criteria into concrete searches and executes them.
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.models.trip_plan import TripPlan
from app.models.trip_plan_match import TripPlanMatch, MatchSource
from app.models.user_settings import UserSettings
from app.scrapers.google_flights import GoogleFlightsScraper, ScrapeResult, FlightResult
from app.services.destination_types import DestinationTypeService
from app.services.airports import AIRPORTS

logger = logging.getLogger(__name__)


@dataclass
class TripPlanSearchResult:
    """Result of a Trip Plan search."""
    origin: str
    destination: str
    departure_date: date
    return_date: Optional[date]
    price_nzd: Decimal
    airline: str
    stops: int
    duration_minutes: int
    booking_url: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TripPlanSearchSummary:
    """Summary of all searches for a Trip Plan."""
    trip_plan_id: int
    searches_attempted: int
    searches_successful: int
    results: list[TripPlanSearchResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: int = 0


class TripPlanSearchService:
    """
    Service for actively searching prices for Trip Plans.
    
    Expands flexible Trip Plan criteria into concrete searches:
    1. Gets user's home airports (origins)
    2. Expands destination types to specific airports
    3. Generates date combinations within the travel window
    4. Executes searches (rate-limited to avoid blocks)
    5. Returns sorted results (cheapest first)
    """
    
    MAX_SEARCHES_PER_PLAN = 6
    SEARCH_DELAY_SECONDS = 3
    
    def __init__(self, db: Session):
        self.db = db
        self.scraper = GoogleFlightsScraper()
    
    async def search_trip_plan(self, trip_plan_id: int) -> TripPlanSearchSummary:
        """
        Execute searches for a Trip Plan and return results.
        
        Returns top results sorted by price (cheapest first).
        """
        start_time = datetime.utcnow()
        
        trip = self.db.query(TripPlan).filter(TripPlan.id == trip_plan_id).first()
        if not trip:
            return TripPlanSearchSummary(
                trip_plan_id=trip_plan_id,
                searches_attempted=0,
                searches_successful=0,
                errors=["Trip plan not found"]
            )
        
        # Get user settings for home airport
        settings = UserSettings.get_or_create(self.db)
        
        # Determine origins
        origins = self._get_origins(trip, settings)
        if not origins:
            return TripPlanSearchSummary(
                trip_plan_id=trip_plan_id,
                searches_attempted=0,
                searches_successful=0,
                errors=["No origins configured - set home airport in settings"]
            )
        
        # Determine destinations
        destinations = self._get_destinations(trip)
        if not destinations:
            return TripPlanSearchSummary(
                trip_plan_id=trip_plan_id,
                searches_attempted=0,
                searches_successful=0,
                errors=["No destinations configured - add destination types or specific destinations"]
            )
        
        date_combos, date_error = self._generate_date_combinations(trip)
        if not date_combos:
            return TripPlanSearchSummary(
                trip_plan_id=trip_plan_id,
                searches_attempted=0,
                searches_successful=0,
                errors=[date_error or "No valid date range"]
            )
        
        # Generate search combinations (limited)
        search_combos = self._generate_search_combinations(origins, destinations, date_combos)
        
        # Execute searches
        all_results: list[TripPlanSearchResult] = []
        errors: list[str] = []
        searches_successful = 0
        
        for i, combo in enumerate(search_combos):
            origin, dest, dep_date, ret_date = combo
            
            logger.info(f"Trip Plan {trip_plan_id}: Searching {origin}->{dest} on {dep_date}")
            
            try:
                result = await self.scraper.scrape_route(
                    search_definition_id=trip_plan_id * 10000 + i,  # Pseudo ID for artifacts
                    origin=origin,
                    destination=dest,
                    departure_date=dep_date,
                    return_date=ret_date,
                    adults=trip.travelers_adults or 2,
                    children=trip.travelers_children or 0,
                    cabin_class=getattr(trip, 'cabin_class', 'economy') or 'economy',
                    currency=getattr(trip, 'currency', 'NZD') or 'NZD',
                )
                
                if result.is_success and result.prices:
                    searches_successful += 1
                    for flight in result.prices:
                        all_results.append(TripPlanSearchResult(
                            origin=origin,
                            destination=dest,
                            departure_date=dep_date,
                            return_date=ret_date,
                            price_nzd=flight.price_nzd,
                            airline=flight.airline,
                            stops=flight.stops,
                            duration_minutes=flight.duration_minutes,
                            booking_url=self._build_booking_url(origin, dest, dep_date, ret_date),
                        ))
                elif result.error_message:
                    errors.append(f"{origin}->{dest}: {result.error_message}")
                    
            except Exception as e:
                errors.append(f"{origin}->{dest}: {str(e)}")
            
            # Delay between searches to avoid rate limiting
            if i < len(search_combos) - 1:
                await asyncio.sleep(self.SEARCH_DELAY_SECONDS)
        
        # Sort results by price
        all_results.sort(key=lambda x: x.price_nzd)

        logger.info(f"Trip Plan {trip_plan_id}: {len(all_results)} total results before budget filter")

        # Filter by budget if set
        if trip.budget_max:
            budget = Decimal(str(trip.budget_max))
            before_count = len(all_results)
            all_results = [r for r in all_results if Decimal(str(r.price_nzd)) <= budget]
            logger.info(f"Trip Plan {trip_plan_id}: Budget filter {budget} {trip.budget_currency}: {before_count} -> {len(all_results)} results")

        # Filter obviously bogus prices (international flights under $200 NZD are not real)
        if origins and all_results:
            before_sanity = len(all_results)
            all_results = [r for r in all_results if self._passes_sanity_check(r)]
            if before_sanity != len(all_results):
                logger.info(f"Trip Plan {trip_plan_id}: Sanity filter removed {before_sanity - len(all_results)} implausible results")

        top_results = self._keep_top_per_destination(all_results, top_n=3)
        logger.info(f"Trip Plan {trip_plan_id}: {len(top_results)} results after top-per-destination filter")

        self._persist_matches(trip, top_results, max_matches=10)
        
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return TripPlanSearchSummary(
            trip_plan_id=trip_plan_id,
            searches_attempted=len(search_combos),
            searches_successful=searches_successful,
            results=top_results,
            errors=errors[:5],  # Limit errors returned
            duration_ms=duration_ms
        )
    
    def _get_origins(self, trip: TripPlan, settings: UserSettings) -> list[str]:
        """Get list of origin airports."""
        if trip.origins:
            return [o.upper() for o in trip.origins if o]
        
        # Fall back to user's home airport
        if settings.home_airport:
            return [settings.home_airport.upper()]
        
        # Default to Auckland
        return ["AKL"]
    
    def _get_destinations(self, trip: TripPlan) -> list[str]:
        """
        Get list of destination airports.
        
        Expands destination_types (like "japan") to specific airports.
        """
        destinations = set()
        
        # Add explicit destinations
        if trip.destinations:
            for d in trip.destinations:
                if d and d.upper() in AIRPORTS:
                    destinations.add(d.upper())
        
        # Expand destination types
        if trip.destination_types:
            type_airports = DestinationTypeService.get_airports_for_types(trip.destination_types)
            destinations.update(type_airports)
        
        return list(destinations)
    
    def _generate_date_combinations(self, trip: TripPlan) -> tuple[list[tuple[date, Optional[date]]], Optional[str]]:
        combos = []
        today = date.today()
        
        if not trip.available_from or not trip.available_to:
            start = today + timedelta(days=60)
            end = today + timedelta(days=90)
        else:
            start = trip.available_from.date() if hasattr(trip.available_from, 'date') else trip.available_from
            end = trip.available_to.date() if hasattr(trip.available_to, 'date') else trip.available_to
        
        min_search_date = today + timedelta(days=14)
        max_search_date = today + timedelta(days=300)
        
        effective_start = max(start, min_search_date)
        effective_end = min(end, max_search_date)
        
        if start > max_search_date:
            days_until = (start - today).days
            searchable_date = start.strftime('%b %d, %Y')
            return [], f"Trip starts {searchable_date} ({days_until} days away). Google Flights only has data ~10 months out. We'll start monitoring when dates become available."
        
        if effective_start > effective_end:
            return [], "No overlap between your travel window and searchable dates (next 10 months)"
        
        min_days = trip.trip_duration_min or 5
        max_days = trip.trip_duration_max or 14
        mid_days = (min_days + max_days) // 2
        
        window_days = (effective_end - effective_start).days
        
        if window_days < mid_days:
            return [], f"Searchable window ({window_days} days) is shorter than minimum trip duration ({mid_days} days)"
        
        dep1 = effective_start + timedelta(days=14)
        if dep1 + timedelta(days=mid_days) <= effective_end:
            combos.append((dep1, dep1 + timedelta(days=mid_days)))
        
        if window_days > 60:
            dep2 = effective_start + timedelta(days=window_days // 3)
            ret2 = dep2 + timedelta(days=mid_days)
            if ret2 <= effective_end and (dep2, ret2) not in combos:
                combos.append((dep2, ret2))
            
            dep3 = effective_start + timedelta(days=(window_days * 2) // 3)
            ret3 = dep3 + timedelta(days=mid_days)
            if ret3 <= effective_end and (dep3, ret3) not in combos:
                combos.append((dep3, ret3))
        elif window_days > 30:
            mid_point = effective_start + timedelta(days=window_days // 2)
            ret2 = mid_point + timedelta(days=mid_days)
            if ret2 <= effective_end and (mid_point, ret2) not in combos:
                combos.append((mid_point, ret2))
        
        return combos[:5], None
    
    def _generate_search_combinations(
        self,
        origins: list[str],
        destinations: list[str],
        date_combos: list[tuple[date, Optional[date]]]
    ) -> list[tuple[str, str, date, Optional[date]]]:
        """
        Generate search combinations, limited to MAX_SEARCHES_PER_PLAN.
        
        Prioritizes:
        1. Primary origin (first in list)
        2. Spread across destinations
        3. Middle dates (usually best prices)
        """
        combos = []
        
        # Use primary origin only to save searches
        origin = origins[0]
        
        # Prioritize middle date combo (index 1 if exists)
        date_priority = [1, 0, 2] if len(date_combos) > 1 else [0]
        
        for date_idx in date_priority:
            if date_idx >= len(date_combos):
                continue
            dep_date, ret_date = date_combos[date_idx]
            
            for dest in destinations:
                if origin == dest:
                    continue
                combos.append((origin, dest, dep_date, ret_date))
                
                if len(combos) >= self.MAX_SEARCHES_PER_PLAN:
                    return combos
        
        return combos
    
    @staticmethod
    def _passes_sanity_check(result: 'TripPlanSearchResult') -> bool:
        """Reject prices that are obviously wrong (e.g. $128 international flights)."""
        price = float(result.price_nzd)
        if price <= 0:
            return False
        # International flights under $200 NZD are almost certainly extraction errors
        if result.origin[:1] != result.destination[:1] and price < 200:
            return False
        # Nonstop with 0 duration is bogus
        if result.stops == 0 and result.duration_minutes == 0 and price < 500:
            return False
        return True

    def _keep_top_per_destination(
        self,
        results: list[TripPlanSearchResult],
        top_n: int = 3
    ) -> list[TripPlanSearchResult]:
        """Keep top N cheapest results per destination."""
        by_dest: dict[str, list[TripPlanSearchResult]] = {}
        
        for r in results:
            if r.destination not in by_dest:
                by_dest[r.destination] = []
            by_dest[r.destination].append(r)
        
        top_results = []
        for dest, dest_results in by_dest.items():
            # Already sorted by price, take top N
            top_results.extend(dest_results[:top_n])
        
        # Sort final list by price
        top_results.sort(key=lambda x: x.price_nzd)
        return top_results
    
    def _build_booking_url(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date]
    ) -> str:
        """Build Google Flights URL for booking via centralized builder."""
        from app.utils.template_helpers import build_google_flights_url
        return build_google_flights_url(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
        )
    
    def _persist_matches(
        self,
        trip: TripPlan,
        results: list[TripPlanSearchResult],
        max_matches: int = 10
    ) -> int:
        today = date.today()
        logger.info(f"Trip {trip.id}: Persisting {len(results)} results (max_matches={max_matches})")

        if not results:
            logger.info(f"Trip {trip.id}: No results to persist")
            return 0

        try:
            expired = self.db.query(TripPlanMatch).filter(
                TripPlanMatch.trip_plan_id == trip.id,
                TripPlanMatch.departure_date < today
            ).delete()
            if expired:
                logger.info(f"Trip {trip.id}: Removed {expired} expired matches")

            added = 0
            updated = 0
            for result in results:
                existing = self.db.query(TripPlanMatch).filter(
                    TripPlanMatch.trip_plan_id == trip.id,
                    TripPlanMatch.origin == result.origin,
                    TripPlanMatch.destination == result.destination,
                    TripPlanMatch.departure_date == result.departure_date,
                    TripPlanMatch.return_date == result.return_date,
                ).first()

                if existing:
                    if result.price_nzd < existing.price_nzd:
                        existing.price_nzd = result.price_nzd
                        existing.airline = result.airline
                        existing.stops = result.stops
                        existing.duration_minutes = result.duration_minutes
                        existing.booking_url = result.booking_url
                        existing.updated_at = datetime.utcnow()
                        updated += 1
                else:
                    match = TripPlanMatch(
                        trip_plan_id=trip.id,
                        source=MatchSource.GOOGLE_FLIGHTS.value,
                        origin=result.origin,
                        destination=result.destination,
                        departure_date=result.departure_date,
                        return_date=result.return_date,
                        price_nzd=Decimal(str(result.price_nzd)),
                        airline=result.airline,
                        stops=result.stops,
                        duration_minutes=result.duration_minutes,
                        booking_url=result.booking_url,
                        match_score=Decimal("50"),
                    )
                    self.db.add(match)
                    added += 1

            self.db.commit()
            logger.info(f"Trip {trip.id}: Added {added}, updated {updated} matches")

            all_matches = self.db.query(TripPlanMatch).filter(
                TripPlanMatch.trip_plan_id == trip.id,
                TripPlanMatch.source == MatchSource.GOOGLE_FLIGHTS.value,
                TripPlanMatch.departure_date >= today
            ).order_by(TripPlanMatch.price_nzd).all()

            for i, match in enumerate(all_matches):
                base_score = 90 - (i * 3)
                if trip.budget_max:
                    budget = Decimal(str(trip.budget_max))
                    if match.price_nzd < budget * Decimal("0.5"):
                        base_score += 10
                    elif match.price_nzd < budget * Decimal("0.75"):
                        base_score += 5
                match.match_score = Decimal(str(min(100, max(0, base_score))))

                if i >= max_matches:
                    self.db.delete(match)

            # Update the trip plan's match_count to include flight matches
            trip.match_count = (trip.match_count or 0)
            flight_count = min(len(all_matches), max_matches)
            # Set match_count to at least the flight match count
            if flight_count > trip.match_count:
                trip.match_count = flight_count
                trip.last_match_at = datetime.utcnow()

            self.db.commit()
            logger.info(f"Trip {trip.id}: Scored and kept {flight_count} matches")
            return flight_count
        except Exception as e:
            logger.error(f"Trip {trip.id}: Failed to persist matches: {e}", exc_info=True)
            self.db.rollback()
            return 0
    
    async def close(self):
        await self.scraper.close()
