import asyncio
import httpx
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Literal

from app.config import get_settings

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


class PriceSource(ABC):
    name: str = "base"
    
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
    ) -> FetchResult:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass


class SerpAPISource(PriceSource):
    name = "serpapi"
    
    def __init__(self):
        self.api_key = getattr(settings, 'serpapi_key', None) or ""
    
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
            
            if return_date:
                params["return_date"] = return_date.isoformat()
                params["type"] = "1"
            else:
                params["type"] = "2"
            
            cabin_map = {"economy": "1", "premium_economy": "2", "business": "3", "first": "4"}
            params["travel_class"] = cabin_map.get(cabin_class, "1")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params=params
                )
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
                except (ValueError, KeyError) as e:
                    logger.debug(f"Failed to parse SerpAPI flight: {e}")
                    continue
            
            if prices:
                logger.info(f"SerpAPI returned {len(prices)} prices for {origin}-{destination}")
                return FetchResult(success=True, prices=prices, source=self.name)
            else:
                return FetchResult(success=False, source=self.name, error="No prices in response")
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"SerpAPI HTTP error: {e.response.status_code}")
            return FetchResult(success=False, source=self.name, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            logger.warning(f"SerpAPI error: {e}")
            return FetchResult(success=False, source=self.name, error=str(e))


class SkyscannerSource(PriceSource):
    name = "skyscanner"
    
    def __init__(self):
        self.api_key = getattr(settings, 'skyscanner_api_key', None) or ""
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
    ) -> FetchResult:
        if not self.is_available():
            return FetchResult(success=False, source=self.name, error="API key not configured")
        
        try:
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": self.api_host,
            }
            
            cabin_map = {"economy": "economy", "premium_economy": "premium_economy", 
                        "business": "business", "first": "first"}
            
            params = {
                "origin": origin,
                "destination": destination,
                "date": departure_date.isoformat(),
                "adults": adults,
                "children": children,
                "currency": currency,
                "cabinClass": cabin_map.get(cabin_class, "economy"),
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
                except (ValueError, KeyError, IndexError) as e:
                    logger.debug(f"Failed to parse Skyscanner itinerary: {e}")
                    continue
            
            if prices:
                logger.info(f"Skyscanner returned {len(prices)} prices for {origin}-{destination}")
                return FetchResult(success=True, prices=prices, source=self.name)
            else:
                return FetchResult(success=False, source=self.name, error="No prices in response")
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"Skyscanner HTTP error: {e.response.status_code}")
            return FetchResult(success=False, source=self.name, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            logger.warning(f"Skyscanner error: {e}")
            return FetchResult(success=False, source=self.name, error=str(e))


class AmadeusSource(PriceSource):
    name = "amadeus"
    
    def __init__(self):
        self.client_id = getattr(settings, 'amadeus_client_id', None) or ""
        self.client_secret = getattr(settings, 'amadeus_client_secret', None) or ""
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
                expires_in = data.get("expires_in", 1799)
                self._token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 60)
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
    ) -> FetchResult:
        if not self.is_available():
            return FetchResult(success=False, source=self.name, error="API credentials not configured")
        
        token = await self._get_token()
        if not token:
            return FetchResult(success=False, source=self.name, error="Failed to authenticate")
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            
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
            
            if return_date:
                params["returnDate"] = return_date.isoformat()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.amadeus.com/v2/shopping/flight-offers",
                    headers=headers,
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
                except (ValueError, KeyError, IndexError) as e:
                    logger.debug(f"Failed to parse Amadeus offer: {e}")
                    continue
            
            if prices:
                logger.info(f"Amadeus returned {len(prices)} prices for {origin}-{destination}")
                return FetchResult(success=True, prices=prices, source=self.name)
            else:
                return FetchResult(success=False, source=self.name, error="No prices in response")
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"Amadeus HTTP error: {e.response.status_code}")
            return FetchResult(success=False, source=self.name, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            logger.warning(f"Amadeus error: {e}")
            return FetchResult(success=False, source=self.name, error=str(e))


class FlightPriceFetcher:
    def __init__(self):
        self.sources: List[PriceSource] = [
            SerpAPISource(),
            SkyscannerSource(),
            AmadeusSource(),
        ]
    
    def get_available_sources(self) -> List[str]:
        return [s.name for s in self.sources if s.is_available()]
    
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
        preferred_source: Optional[str] = None,
    ) -> FetchResult:
        sources_to_try = list(self.sources)
        
        if preferred_source:
            sources_to_try = sorted(
                sources_to_try,
                key=lambda s: 0 if s.name == preferred_source else 1
            )
        
        last_error = "No sources available"
        fallback_used = False
        
        for i, source in enumerate(sources_to_try):
            if not source.is_available():
                logger.debug(f"Skipping {source.name} - not configured")
                continue
            
            logger.info(f"Trying {source.name} for {origin}-{destination}")
            
            result = await source.fetch_prices(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                children=children,
                cabin_class=cabin_class,
                currency=currency,
            )
            
            if result.success:
                result.fallback_used = (i > 0)
                return result
            
            last_error = f"{source.name}: {result.error}"
            fallback_used = True
            
            await asyncio.sleep(0.5)
        
        if not any(s.is_available() for s in self.sources):
            return FetchResult(
                success=False,
                source="none",
                error="No price sources configured. Add API keys in Settings.",
            )
        
        return FetchResult(
            success=False,
            source="all_failed",
            error=f"All sources failed. Last error: {last_error}",
            fallback_used=fallback_used,
        )


from datetime import timedelta
