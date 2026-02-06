"""
Seats.aero API client for award flight availability.

API docs: https://developers.seats.aero/reference/overview
Authentication: Partner-Authorization header with Bearer token.
Rate limit: 1,000 calls/day for Pro users.
"""
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://seats.aero/partnerapi"

# Cabin class mapping: Seats.aero uses single-letter codes
CABIN_MAP = {
    "economy": "Y",
    "premium_economy": "W",
    "business": "J",
    "first": "F",
}

CABIN_REVERSE = {v: k for k, v in CABIN_MAP.items()}


@dataclass
class AwardResult:
    """A single award availability result from the API."""
    origin: str
    destination: str
    date: str  # YYYY-MM-DD
    program: str
    cabin: str  # economy, premium_economy, business, first
    miles: int
    taxes_usd: float = 0.0
    seats_available: int = 0
    is_direct: bool = False
    airline: str = ""
    raw: dict = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Response from a Seats.aero search."""
    results: list[AwardResult]
    has_more: bool = False
    cursor: str = ""
    total_count: int = 0


class SeatsAeroClient:
    """
    Rate-limited Seats.aero API client.

    Usage:
        client = SeatsAeroClient(api_key="your_key")
        results = await client.search_availability("AKL", "SYD", "2026-03-01", "2026-03-15")
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=BASE_URL,
                headers={
                    "Partner-Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def search_availability(
        self,
        origin: str,
        destination: str,
        start_date: str,
        end_date: str,
        cabin: str = "business",
        program: Optional[str] = None,
        direct_only: bool = False,
        take: int = 500,
    ) -> SearchResponse:
        """
        Search for award availability between two airports.

        Args:
            origin: Origin IATA code (e.g., "AKL")
            destination: Destination IATA code (e.g., "SYD")
            start_date: Start of date range (YYYY-MM-DD)
            end_date: End of date range (YYYY-MM-DD)
            cabin: Cabin class (economy, premium_economy, business, first)
            program: Filter by program (e.g., "united") or None for all
            direct_only: Only return direct flights
            take: Number of results per page (10-1000)

        Returns:
            SearchResponse with parsed results
        """
        client = await self._get_client()

        params = {
            "origin_airport": origin.upper(),
            "destination_airport": destination.upper(),
            "start_date": start_date,
            "end_date": end_date,
            "take": min(take, 1000),
        }

        if program:
            params["source"] = program

        cabin_code = CABIN_MAP.get(cabin, "J")

        try:
            response = await client.get("/availability", params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Seats.aero API error: {e.response.status_code} - {e.response.text[:200]}")
            return SearchResponse(results=[])
        except httpx.RequestError as e:
            logger.error(f"Seats.aero request failed: {e}")
            return SearchResponse(results=[])

        results = []
        items = data.get("data", [])
        for item in items:
            # Check cabin availability
            avail_key = f"{cabin_code}Available"
            if not item.get(avail_key, False):
                continue

            # Check direct filter
            if direct_only and not item.get("isDirect", False):
                continue

            miles_key = f"{cabin_code}MileageCost"
            seats_key = f"{cabin_code}RemainingSeats"

            miles = item.get(miles_key, 0) or 0
            seats = item.get(seats_key, 0) or 0

            if miles <= 0:
                continue

            results.append(AwardResult(
                origin=item.get("Route", {}).get("OriginAirport", origin),
                destination=item.get("Route", {}).get("DestinationAirport", destination),
                date=item.get("Date", ""),
                program=item.get("Source", ""),
                cabin=cabin,
                miles=miles,
                taxes_usd=item.get("taxes", 0.0) or 0.0,
                seats_available=seats,
                is_direct=item.get("isDirect", False),
                airline=item.get("Route", {}).get("Airline", ""),
                raw=item,
            ))

        return SearchResponse(
            results=results,
            has_more=data.get("hasMore", False),
            cursor=data.get("cursor", ""),
            total_count=len(results),
        )

    async def get_trip_details(self, trip_id: str) -> dict:
        """Get flight-level details for a specific availability result."""
        client = await self._get_client()
        try:
            response = await client.get(f"/trips/{trip_id}")
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"Seats.aero trip details error: {e}")
            return {}


def hash_results(results: list[AwardResult]) -> str:
    """Create a deterministic hash of results for change detection."""
    normalized = sorted(
        [
            {
                "origin": r.origin,
                "destination": r.destination,
                "date": r.date,
                "program": r.program,
                "cabin": r.cabin,
                "miles": r.miles,
                "seats": r.seats_available,
            }
            for r in results
        ],
        key=lambda x: (x["date"], x["program"], x["miles"]),
    )
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
