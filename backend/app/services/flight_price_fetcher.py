import asyncio
import httpx
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Literal

from app.config import get_settings
from app.services.api_keys import get_api_key

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class PriceResult:
    price: Decimal
    currency: str
    airline: Optional[str] = None
    stops: int = 0
    duration_minutes: Optional[int] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    booking_url: Optional[str] = None
    source: str = "unknown"


@dataclass 
class FetchResult:
    success: bool
    prices: List[PriceResult] = field(default_factory=list)
    source: str = "unknown"
    error: Optional[str] = None
    fallback_used: bool = False
    attempts: int = 1


class PriceSource(ABC):
    name: str = "base"
    max_retries: int = 2
    retry_delay: float = 1.0
    
    @abstractmethod
    async def fetch_prices(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int,
        children: int,
        cabin_class: str,
        currency: str,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        stops_filter: str = "any",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
    ) -> FetchResult:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    async def fetch_with_retry(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int,
        children: int,
        cabin_class: str,
        currency: str,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        stops_filter: str = "any",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
    ) -> FetchResult:
        last_error = None

        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                delay = self.retry_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                logger.info(f"{self.name}: Retry {attempt}/{self.max_retries} after {delay:.1f}s")
                await asyncio.sleep(delay)

            result = await self.fetch_prices(
                origin, destination, departure_date, return_date,
                adults, children, cabin_class, currency,
                infants_in_seat=infants_in_seat,
                infants_on_lap=infants_on_lap,
                stops_filter=stops_filter,
                carry_on_bags=carry_on_bags,
                checked_bags=checked_bags,
            )
            result.attempts = attempt + 1
            
            if result.success:
                return result
            
            last_error = result.error
            
            if "not configured" in (result.error or ""):
                break
        
        return FetchResult(
            success=False,
            source=self.name,
            error=last_error,
            attempts=self.max_retries + 1
        )


class SerpAPISource(PriceSource):
    name = "serpapi"

    STOPS_MAP = {"any": 0, "nonstop": 1, "one_stop": 2, "two_plus": 3}

    def __init__(self, db=None):
        self.api_key = get_api_key("serpapi_key", db) or ""

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def fetch_prices(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int,
        children: int,
        cabin_class: str,
        currency: str,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        stops_filter: str = "any",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
    ) -> FetchResult:
        if not self.is_available():
            return FetchResult(success=False, source=self.name, error="API key not configured")

        try:
            params = {
                "engine": "google_flights",
                "departure_id": origin,
                "arrival_id": destination,
                "outbound_date": departure_date.isoformat(),
                "currency": currency,
                "hl": "en",
                "adults": adults,
                "children": children,
                "api_key": self.api_key,
            }

            if infants_in_seat:
                params["infants_in_seat"] = infants_in_seat
            if infants_on_lap:
                params["infants_on_lap"] = infants_on_lap

            stops_val = self.STOPS_MAP.get(stops_filter, 0)
            if stops_val:
                params["stops"] = stops_val

            if carry_on_bags:
                params["bags"] = max(carry_on_bags, checked_bags)
            elif checked_bags:
                params["bags"] = checked_bags

            if return_date:
                params["return_date"] = return_date.isoformat()
                params["type"] = "1"
            else:
                params["type"] = "2"

            cabin_map = {"economy": "1", "premium_economy": "2", "business": "3", "first": "4"}
            params["travel_class"] = cabin_map.get(cabin_class, "1")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get("https://serpapi.com/search", params=params)
                response.raise_for_status()
                data = response.json()
            
            prices = []
            for flight in data.get("best_flights", []) + data.get("other_flights", []):
                try:
                    price_val = flight.get("price")
                    if price_val:
                        flights_info = flight.get("flights", [{}])
                        first_leg = flights_info[0] if flights_info else {}
                        prices.append(PriceResult(
                            price=Decimal(str(price_val)),
                            currency=currency,
                            airline=first_leg.get("airline"),
                            stops=len(flights_info) - 1 if flights_info else 0,
                            duration_minutes=flight.get("total_duration"),
                            departure_time=first_leg.get("departure_airport", {}).get("time"),
                            arrival_time=first_leg.get("arrival_airport", {}).get("time"),
                            source=self.name,
                        ))
                except (ValueError, KeyError):
                    continue
            
            if prices:
                return FetchResult(success=True, prices=prices, source=self.name)
            return FetchResult(success=False, source=self.name, error="No prices in response")
                
        except httpx.HTTPStatusError as e:
            return FetchResult(success=False, source=self.name, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return FetchResult(success=False, source=self.name, error=str(e))


class SkyscannerSource(PriceSource):
    name = "skyscanner"

    def __init__(self, db=None):
        self.api_key = get_api_key("skyscanner_api_key", db) or ""
        self.api_host = "skyscanner44.p.rapidapi.com"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def fetch_prices(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int,
        children: int,
        cabin_class: str,
        currency: str,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        stops_filter: str = "any",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
    ) -> FetchResult:
        if not self.is_available():
            return FetchResult(success=False, source=self.name, error="API key not configured")
        
        try:
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": self.api_host,
            }
            params = {
                "origin": origin,
                "destination": destination,
                "date": departure_date.isoformat(),
                "adults": adults,
                "children": children,
                "currency": currency,
                "cabinClass": cabin_class,
            }
            if return_date:
                params["returnDate"] = return_date.isoformat()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"https://{self.api_host}/search",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            prices = []
            for itinerary in data.get("itineraries", {}).get("results", []):
                try:
                    price_info = itinerary.get("pricing_options", [{}])[0]
                    price_val = price_info.get("price", {}).get("amount")
                    if price_val:
                        leg = itinerary.get("legs", [{}])[0]
                        carriers = leg.get("carriers", {}).get("marketing", [{}])
                        prices.append(PriceResult(
                            price=Decimal(str(price_val)),
                            currency=currency,
                            airline=carriers[0].get("name") if carriers else None,
                            stops=leg.get("stop_count", 0),
                            duration_minutes=leg.get("duration"),
                            source=self.name,
                            booking_url=price_info.get("items", [{}])[0].get("url"),
                        ))
                except (ValueError, KeyError, IndexError):
                    continue
            
            if prices:
                return FetchResult(success=True, prices=prices, source=self.name)
            return FetchResult(success=False, source=self.name, error="No prices in response")
                
        except httpx.HTTPStatusError as e:
            return FetchResult(success=False, source=self.name, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return FetchResult(success=False, source=self.name, error=str(e))


class AmadeusSource(PriceSource):
    name = "amadeus"
    
    def __init__(self, db=None):
        self.client_id = get_api_key("amadeus_client_id", db) or ""
        self.client_secret = get_api_key("amadeus_client_secret", db) or ""
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
                    "https://api.amadeus.com/v1/security/oauth2/token",
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
    
    async def fetch_prices(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int,
        children: int,
        cabin_class: str,
        currency: str,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        stops_filter: str = "any",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
    ) -> FetchResult:
        if not self.is_available():
            return FetchResult(success=False, source=self.name, error="API credentials not configured")

        token = await self._get_token()
        if not token:
            return FetchResult(success=False, source=self.name, error="Failed to authenticate")
        
        try:
            cabin_map = {"economy": "ECONOMY", "premium_economy": "PREMIUM_ECONOMY",
                        "business": "BUSINESS", "first": "FIRST"}
            params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date.isoformat(),
                "adults": adults,
                "children": children,
                "travelClass": cabin_map.get(cabin_class, "ECONOMY"),
                "currencyCode": currency,
                "max": 20,
            }
            if infants_in_seat + infants_on_lap > 0:
                params["infants"] = infants_in_seat + infants_on_lap
            if stops_filter == "nonstop":
                params["nonStop"] = "true"
            if return_date:
                params["returnDate"] = return_date.isoformat()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.amadeus.com/v2/shopping/flight-offers",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params
                )
                response.raise_for_status()
                data = response.json()
            
            prices = []
            for offer in data.get("data", []):
                try:
                    price_val = offer.get("price", {}).get("grandTotal")
                    if price_val:
                        segments = offer.get("itineraries", [{}])[0].get("segments", [])
                        prices.append(PriceResult(
                            price=Decimal(str(price_val)),
                            currency=offer.get("price", {}).get("currency", currency),
                            airline=segments[0].get("carrierCode") if segments else None,
                            stops=len(segments) - 1 if segments else 0,
                            source=self.name,
                        ))
                except (ValueError, KeyError, IndexError):
                    continue
            
            if prices:
                return FetchResult(success=True, prices=prices, source=self.name)
            return FetchResult(success=False, source=self.name, error="No prices in response")
                
        except httpx.HTTPStatusError as e:
            return FetchResult(success=False, source=self.name, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return FetchResult(success=False, source=self.name, error=str(e))


class PlaywrightSource(PriceSource):
    name = "playwright"
    max_retries = 1

    def is_available(self) -> bool:
        return True

    async def fetch_prices(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int,
        children: int,
        cabin_class: str,
        currency: str,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        stops_filter: str = "any",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
    ) -> FetchResult:
        try:
            from app.scrapers.google_flights import GoogleFlightsScraper

            scraper = GoogleFlightsScraper()
            result = await scraper.scrape_route(
                search_definition_id=0,
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                children=children,
                infants_in_seat=infants_in_seat,
                infants_on_lap=infants_on_lap,
                cabin_class=cabin_class,
                stops_filter=stops_filter,
                currency=currency,
                carry_on_bags=carry_on_bags,
                checked_bags=checked_bags,
            )
            
            if result.is_success and result.prices:
                prices = [
                    PriceResult(
                        price=p.price_nzd,
                        currency=currency,
                        airline=p.airline,
                        stops=p.stops,
                        duration_minutes=p.duration_minutes,
                        source=self.name,
                    )
                    for p in result.prices
                ]
                return FetchResult(success=True, prices=prices, source=self.name)
            
            return FetchResult(
                success=False,
                source=self.name,
                error=result.error_message or f"Scrape status: {result.status}"
            )
            
        except ImportError:
            return FetchResult(success=False, source=self.name, error="Playwright not available")
        except Exception as e:
            return FetchResult(success=False, source=self.name, error=str(e))


class AIAnalyzer:
    def __init__(self, db=None):
        self.api_key = get_api_key("anthropic_api_key", db) or ""
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def analyze_prices(
        self,
        prices: List[PriceResult],
        route: str,
        historical_avg: Optional[float] = None,
    ) -> Optional[dict]:
        if not self.is_available() or not prices:
            return None
        
        try:
            price_list = [float(p.price) for p in prices]
            min_price = min(price_list)
            avg_price = sum(price_list) / len(price_list)
            
            prompt = f"""Analyze these flight prices for {route}:
Current prices: {price_list[:5]}
Lowest: ${min_price:.0f}
Average: ${avg_price:.0f}
{"Historical average: $" + f"{historical_avg:.0f}" if historical_avg else "No historical data"}

Provide a brief 1-2 sentence recommendation: Is this a good deal? Should they book now or wait?"""

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 150,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                recommendation = data.get("content", [{}])[0].get("text", "")
                
                return {
                    "recommendation": recommendation,
                    "is_good_deal": min_price < (historical_avg * 0.85) if historical_avg else None,
                    "savings_percent": ((historical_avg - min_price) / historical_avg * 100) if historical_avg else None,
                }
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
            return None


class FlightPriceFetcher:
    def __init__(self, db=None):
        self.sources: List[PriceSource] = [
            SerpAPISource(db=db),
            SkyscannerSource(db=db),
            AmadeusSource(db=db),
            PlaywrightSource(),
        ]
        self.ai_analyzer = AIAnalyzer(db=db)
    
    def get_available_sources(self) -> List[str]:
        return [s.name for s in self.sources if s.is_available()]
    
    def get_status(self) -> dict:
        return {
            "sources": {
                s.name: {"available": s.is_available(), "type": "api" if s.name != "playwright" else "scraper"}
                for s in self.sources
            },
            "ai_enabled": self.ai_analyzer.is_available(),
            "total_available": sum(1 for s in self.sources if s.is_available()),
        }
    
    async def fetch_prices(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        adults: int = 2,
        children: int = 0,
        cabin_class: str = "economy",
        currency: str = "NZD",
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        stops_filter: str = "any",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
        preferred_source: Optional[str] = None,
        include_ai_analysis: bool = True,
        historical_avg: Optional[float] = None,
    ) -> FetchResult:
        sources_to_try = list(self.sources)

        if preferred_source:
            sources_to_try = sorted(
                sources_to_try,
                key=lambda s: 0 if s.name == preferred_source else 1
            )

        last_error = "No sources available"
        fallback_used = False
        total_attempts = 0

        for i, source in enumerate(sources_to_try):
            if not source.is_available():
                logger.debug(f"Skipping {source.name} - not configured")
                continue

            logger.info(f"Trying {source.name} for {origin}-{destination}")

            result = await source.fetch_with_retry(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                children=children,
                cabin_class=cabin_class,
                currency=currency,
                infants_in_seat=infants_in_seat,
                infants_on_lap=infants_on_lap,
                stops_filter=stops_filter,
                carry_on_bags=carry_on_bags,
                checked_bags=checked_bags,
            )
            total_attempts += result.attempts
            
            if result.success:
                result.fallback_used = (i > 0)
                result.attempts = total_attempts
                
                if include_ai_analysis and self.ai_analyzer.is_available():
                    ai_result = await self.ai_analyzer.analyze_prices(
                        result.prices,
                        f"{origin} → {destination}",
                        historical_avg
                    )
                    if ai_result:
                        result.ai_analysis = ai_result
                
                return result
            
            last_error = f"{source.name}: {result.error}"
            fallback_used = True
            await asyncio.sleep(0.5)
        
        return FetchResult(
            success=False,
            source="all_failed",
            error=f"All sources failed. Last: {last_error}",
            fallback_used=fallback_used,
            attempts=total_attempts,
        )
