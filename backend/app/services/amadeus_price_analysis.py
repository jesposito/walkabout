"""
Amadeus Flight Price Analysis API client.

Uses the Itinerary Price Metrics endpoint to retrieve price quartile data
for a given route and departure date.
"""
import httpx
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from app.config import get_settings
from app.services.api_keys import get_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class PriceMetric:
    quartile_ranking: str
    amount: Decimal


@dataclass
class PriceAnalysisResult:
    success: bool
    origin: Optional[str] = None
    destination: Optional[str] = None
    departure_date: Optional[str] = None
    currency: Optional[str] = None
    metrics: List[PriceMetric] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def minimum(self) -> Optional[Decimal]:
        return self._get_metric("MINIMUM")

    @property
    def first_quartile(self) -> Optional[Decimal]:
        return self._get_metric("FIRST")

    @property
    def median(self) -> Optional[Decimal]:
        return self._get_metric("MEDIUM")

    @property
    def third_quartile(self) -> Optional[Decimal]:
        return self._get_metric("THIRD")

    @property
    def maximum(self) -> Optional[Decimal]:
        return self._get_metric("MAXIMUM")

    def _get_metric(self, ranking: str) -> Optional[Decimal]:
        for m in self.metrics:
            if m.quartile_ranking == ranking:
                return m.amount
        return None


class AmadeusPriceAnalysis:
    """Client for the Amadeus Itinerary Price Metrics API."""

    def __init__(self, db=None):
        self.client_id = get_api_key("amadeus_client_id", db) or ""
        self.client_secret = get_api_key("amadeus_client_secret", db) or ""
        self.base_url = settings.amadeus_base_url.rstrip("/")
        self._token: Optional[str] = None
        self._token_expires: Optional[datetime] = None

    def is_available(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _get_token(self) -> Optional[str]:
        if self._token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/v1/security/oauth2/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    }
                )
                response.raise_for_status()
                data = response.json()
                self._token = data["access_token"]
                self._token_expires = datetime.utcnow() + timedelta(seconds=data.get("expires_in", 1799) - 60)
                return self._token
        except Exception as e:
            logger.warning(f"Amadeus auth failed: {e}")
            return None

    async def get_price_metrics(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        currency_code: str = "USD",
        one_way: bool = True,
    ) -> PriceAnalysisResult:
        """Fetch itinerary price metrics for a route.

        Args:
            origin: Origin IATA airport code (e.g. "AKL").
            destination: Destination IATA airport code (e.g. "SYD").
            departure_date: Date of departure.
            currency_code: Currency for prices (default "USD").
            one_way: True for one-way, False for round-trip.

        Returns:
            PriceAnalysisResult with quartile price data.
        """
        if not self.is_available():
            return PriceAnalysisResult(
                success=False,
                error="API credentials not configured",
            )

        token = await self._get_token()
        if not token:
            return PriceAnalysisResult(
                success=False,
                error="Failed to authenticate",
            )

        try:
            params = {
                "originIataCode": origin,
                "destinationIataCode": destination,
                "departureDate": departure_date.isoformat(),
                "currencyCode": currency_code,
                "oneWay": str(one_way).lower(),
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/v1/analytics/itinerary-price-metrics",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            results = data.get("data", [])
            if not results:
                return PriceAnalysisResult(
                    success=False,
                    error="No price metric data in response",
                )

            first = results[0]
            metrics = []
            for pm in first.get("priceMetrics", []):
                try:
                    metrics.append(PriceMetric(
                        quartile_ranking=pm["quartileRanking"],
                        amount=Decimal(pm["amount"]),
                    ))
                except (KeyError, ValueError):
                    continue

            return PriceAnalysisResult(
                success=True,
                origin=first.get("origin", {}).get("iataCode"),
                destination=first.get("destination", {}).get("iataCode"),
                departure_date=first.get("departureDate"),
                currency=currency_code,
                metrics=metrics,
            )

        except httpx.HTTPStatusError as e:
            return PriceAnalysisResult(
                success=False,
                error=f"HTTP {e.response.status_code}",
            )
        except Exception as e:
            return PriceAnalysisResult(
                success=False,
                error=str(e),
            )
