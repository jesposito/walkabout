"""
Award availability polling service.

Polls Seats.aero for tracked award searches and stores observations.
Uses hash-based change detection to avoid duplicate notifications.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.award import TrackedAwardSearch, AwardObservation
from app.models.user_settings import UserSettings
from app.services.seats_aero import SeatsAeroClient, hash_results, AwardResult

logger = logging.getLogger(__name__)


class AwardPoller:
    """
    Polls Seats.aero for tracked award searches.

    Rate limit awareness: Seats.aero allows ~1000 calls/day.
    With 10 tracked searches polled once daily, that's well within limits.
    """

    def __init__(self, db: Session):
        self.db = db

    async def poll_all(self) -> dict:
        """
        Poll all active tracked searches.

        Returns summary: {polled: N, changed: N, errors: N}
        """
        settings = UserSettings.get_or_create(self.db)
        api_key = self._get_api_key(settings)
        if not api_key:
            logger.warning("No Seats.aero API key configured, skipping award polling")
            return {"polled": 0, "changed": 0, "errors": 0, "skipped_reason": "no_api_key"}

        searches = self.db.query(TrackedAwardSearch).filter(
            TrackedAwardSearch.is_active == True
        ).all()

        if not searches:
            return {"polled": 0, "changed": 0, "errors": 0}

        client = SeatsAeroClient(api_key)
        summary = {"polled": 0, "changed": 0, "errors": 0}

        try:
            for search in searches:
                try:
                    changed = await self._poll_search(client, search)
                    summary["polled"] += 1
                    if changed:
                        summary["changed"] += 1
                except Exception as e:
                    logger.error(f"Error polling award search {search.id}: {e}")
                    summary["errors"] += 1
        finally:
            await client.close()

        self.db.commit()
        logger.info(f"Award polling complete: {summary}")
        return summary

    async def poll_single(self, search_id: int) -> Optional[AwardObservation]:
        """Poll a single tracked search. Returns the observation if created."""
        settings = UserSettings.get_or_create(self.db)
        api_key = self._get_api_key(settings)
        if not api_key:
            return None

        search = self.db.query(TrackedAwardSearch).filter(
            TrackedAwardSearch.id == search_id
        ).first()
        if not search:
            return None

        client = SeatsAeroClient(api_key)
        try:
            await self._poll_search(client, search)
            self.db.commit()
            return search.observations[0] if search.observations else None
        finally:
            await client.close()

    async def _poll_search(self, client: SeatsAeroClient, search: TrackedAwardSearch) -> bool:
        """
        Poll a single search and store the observation.

        Returns True if results changed from last observation.
        """
        start_date = search.date_start.strftime("%Y-%m-%d") if search.date_start else None
        end_date = search.date_end.strftime("%Y-%m-%d") if search.date_end else None

        if not start_date or not end_date:
            logger.warning(f"Award search {search.id} missing date range, skipping")
            return False

        response = await client.search_availability(
            origin=search.origin,
            destination=search.destination,
            start_date=start_date,
            end_date=end_date,
            cabin=search.cabin_class or "business",
            program=search.program,
            direct_only=search.direct_only,
        )

        # Apply min_seats filter
        if search.min_seats and search.min_seats > 1:
            response.results = [
                r for r in response.results
                if r.seats_available >= search.min_seats
            ]

        # Hash for change detection
        result_hash = hash_results(response.results)
        is_changed = result_hash != search.last_hash

        # Extract summary fields
        programs = list(set(r.program for r in response.results))
        best_economy = self._best_miles(response.results, "economy")
        best_business = self._best_miles(response.results, "business")
        best_first = self._best_miles(response.results, "first")
        max_seats = max((r.seats_available for r in response.results), default=0)

        # Create observation
        observation = AwardObservation(
            search_id=search.id,
            payload_hash=result_hash,
            is_changed=is_changed,
            programs_with_availability=programs,
            best_economy_miles=best_economy,
            best_business_miles=best_business,
            best_first_miles=best_first,
            total_options=len(response.results),
            max_seats_available=max_seats,
            raw_results=[
                {
                    "origin": r.origin,
                    "destination": r.destination,
                    "date": r.date,
                    "program": r.program,
                    "cabin": r.cabin,
                    "miles": r.miles,
                    "seats": r.seats_available,
                    "direct": r.is_direct,
                    "airline": r.airline,
                }
                for r in response.results
            ],
        )
        self.db.add(observation)

        # Update search tracking
        search.last_polled_at = datetime.utcnow()
        search.last_hash = result_hash

        if is_changed:
            logger.info(
                f"Award search {search.id} ({search.origin}-{search.destination}): "
                f"{len(response.results)} results, CHANGED"
            )
        else:
            logger.debug(
                f"Award search {search.id} ({search.origin}-{search.destination}): "
                f"{len(response.results)} results, unchanged"
            )

        return is_changed

    @staticmethod
    def _best_miles(results: list[AwardResult], cabin: str) -> Optional[int]:
        cabin_results = [r for r in results if r.cabin == cabin and r.miles > 0]
        if not cabin_results:
            return None
        return min(r.miles for r in cabin_results)

    @staticmethod
    def _get_api_key(settings: UserSettings) -> Optional[str]:
        """Get Seats.aero API key from settings. Could be stored as a dedicated field or via ai_api_key."""
        # Check for dedicated seats_aero key in settings (future)
        # For now, check if there's a key in the settings or environment
        import os
        return os.environ.get("SEATS_AERO_API_KEY")
