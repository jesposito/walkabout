from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import re
import hashlib
import feedparser
import httpx
import logging
import asyncio

from app.models.deal import DealSource, ParseStatus
from app.services.airports import AIRPORTS

logger = logging.getLogger(__name__)

VALID_AIRPORT_CODES = set(AIRPORTS.keys())

CITY_TO_AIRPORT = {}
COUNTRY_TO_AIRPORTS = {}
for code, airport in AIRPORTS.items():
    city_key = airport.city.lower()
    if city_key not in CITY_TO_AIRPORT:
        CITY_TO_AIRPORT[city_key] = code
    country_key = airport.country.lower()
    if country_key not in COUNTRY_TO_AIRPORTS:
        COUNTRY_TO_AIRPORTS[country_key] = []
    COUNTRY_TO_AIRPORTS[country_key].append(code)

CITY_TO_AIRPORT.update({
    'tokyo': 'NRT',
    'london': 'LHR', 
    'new york': 'JFK',
    'nyc': 'JFK',
    'la': 'LAX',
    'los angeles': 'LAX',
    'san francisco': 'SFO',
    'sf': 'SFO',
    'paris': 'CDG',
    'hawaii': 'HNL',
    'bali': 'DPS',
    'phuket': 'HKT',
    'fiji': 'NAN',
    'rarotonga': 'RAR',
    'cook islands': 'RAR',
    'tahiti': 'PPT',
    'japan': 'NRT',
    'singapore': 'SIN',
    'hong kong': 'HKG',
    'dubai': 'DXB',
    'bangkok': 'BKK',
    'seoul': 'ICN',
})

MAX_RETRIES = 3
RETRY_DELAY = 2.0


@dataclass
class ParseResult:
    origin: Optional[str] = None
    destination: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    travel_dates: Optional[str] = None
    airline: Optional[str] = None
    cabin_class: Optional[str] = None
    
    confidence: float = 0.0
    status: ParseStatus = ParseStatus.PENDING
    reasons: list[str] = field(default_factory=list)
    parser_used: str = "none"
    

@dataclass
class ParsedDeal:
    source: DealSource
    guid: Optional[str]
    link: str
    published_at: Optional[datetime]
    raw_title: str
    raw_summary: Optional[str]
    raw_content_html: Optional[str]
    
    result: ParseResult = field(default_factory=ParseResult)
    
    input_hash: Optional[str] = None
    
    def compute_input_hash(self) -> str:
        normalized = self._normalize_for_hash(self.raw_title)
        self.input_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return self.input_hash
    
    def _normalize_for_hash(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(limited time|book now|hurry|alert|deal)', '', text, flags=re.IGNORECASE)
        return text


class ConfidenceScorer:
    
    REQUIRED_FIELDS = ['origin', 'destination']
    PRICE_BOUNDS = (20, 15000)
    VALID_CURRENCIES = {'USD', 'EUR', 'GBP', 'NZD', 'AUD', 'CAD', 'SGD', 'JPY'}
    VALID_CABINS = {'economy', 'premium_economy', 'business', 'first', None}
    
    @classmethod
    def score(cls, result: ParseResult) -> tuple[float, list[str]]:
        score = 0.0
        max_score = 0.0
        reasons = []
        
        max_score += 0.3
        if result.origin and result.destination:
            if result.origin != result.destination:
                score += 0.3
            else:
                reasons.append("origin equals destination")
        else:
            reasons.append("missing origin or destination")
        
        max_score += 0.25
        if result.price:
            if cls.PRICE_BOUNDS[0] <= result.price <= cls.PRICE_BOUNDS[1]:
                score += 0.25
            else:
                reasons.append(f"price {result.price} outside bounds")
        else:
            reasons.append("no price extracted")
        
        max_score += 0.15
        if result.currency:
            if result.currency.upper() in cls.VALID_CURRENCIES:
                score += 0.15
            else:
                reasons.append(f"unknown currency {result.currency}")
        
        max_score += 0.1
        if result.cabin_class in cls.VALID_CABINS:
            score += 0.1
        
        max_score += 0.1
        if result.airline:
            score += 0.1
        
        max_score += 0.1
        if result.origin and len(result.origin) == 3 and result.origin.isupper():
            score += 0.05
        if result.destination and len(result.destination) == 3 and result.destination.isupper():
            score += 0.05
        
        confidence = score / max_score if max_score > 0 else 0.0
        return (confidence, reasons)


class BaseFeedParser(ABC):
    
    AIRPORT_PATTERN = re.compile(r'\b([A-Z]{3})\b')
    PRICE_PATTERN = re.compile(r'[\$€£]?\s*(\d{1,2}[,.]?\d{3}|\d{2,4})\s*(?:USD|EUR|GBP|NZD|AUD)?', re.IGNORECASE)
    
    def __init__(self, feed_url: str, source: DealSource):
        self.feed_url = feed_url
        self.source = source
        self.timeout = 30.0
    
    async def fetch_feed(self) -> list[ParsedDeal]:
        last_error = None
        
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        self.feed_url,
                        headers={"User-Agent": "Walkabout/1.0 (Personal Flight Deal Monitor)"},
                        follow_redirects=True,
                    )
                    response.raise_for_status()
                    
                feed = feedparser.parse(response.text)
                
                if feed.bozo and feed.bozo_exception:
                    logger.warning(f"Feed parse warning for {self.source.value}: {feed.bozo_exception}")
                
                if not feed.entries:
                    logger.warning(f"No entries found in {self.source.value} feed")
                    return []
                
                deals = []
                for entry in feed.entries:
                    try:
                        deal = self._parse_entry(entry)
                        deal.compute_input_hash()
                        deals.append(deal)
                    except Exception as e:
                        logger.error(f"Failed to parse entry from {self.source.value}: {e}")
                        deals.append(self._create_failed_deal(entry, str(e)))
                
                return deals
                
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Timeout fetching {self.source.value} (attempt {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503, 502, 504):
                    last_error = e
                    logger.warning(f"Retryable HTTP {e.response.status_code} for {self.source.value}")
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"HTTP {e.response.status_code} fetching {self.source.value}")
                    raise
            except Exception as e:
                logger.error(f"Error fetching {self.source.value}: {e}")
                raise
        
        logger.error(f"All {MAX_RETRIES} retries failed for {self.source.value}")
        raise last_error or Exception(f"Failed to fetch {self.source.value}")
    
    def _parse_entry(self, entry) -> ParsedDeal:
        deal = ParsedDeal(
            source=self.source,
            guid=getattr(entry, 'id', None),
            link=entry.link,
            published_at=self._parse_date(entry),
            raw_title=entry.title,
            raw_summary=getattr(entry, 'summary', None),
            raw_content_html=self._get_content_html(entry),
        )
        
        result = self.extract_deal_details(deal)
        
        confidence, reasons = ConfidenceScorer.score(result)
        result.confidence = confidence
        result.reasons = reasons
        
        if confidence >= 0.6 and result.origin and result.destination:
            result.status = ParseStatus.SUCCESS
        elif confidence >= 0.3 or result.price:
            result.status = ParseStatus.PARTIAL
        else:
            result.status = ParseStatus.FAILED
        
        deal.result = result
        return deal
    
    @abstractmethod
    def extract_deal_details(self, deal: ParsedDeal) -> ParseResult:
        pass
    
    def _parse_date(self, entry) -> Optional[datetime]:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                return datetime(*entry.published_parsed[:6])
            except (ValueError, TypeError):
                pass
        return None
    
    def _get_content_html(self, entry) -> Optional[str]:
        if hasattr(entry, 'content') and entry.content:
            return entry.content[0].get('value')
        return getattr(entry, 'summary', None)
    
    def _create_failed_deal(self, entry, error: str) -> ParsedDeal:
        deal = ParsedDeal(
            source=self.source,
            guid=getattr(entry, 'id', None),
            link=getattr(entry, 'link', 'unknown'),
            published_at=None,
            raw_title=getattr(entry, 'title', 'Parse Failed'),
            raw_summary=getattr(entry, 'summary', None),
            raw_content_html=None,
        )
        deal.result = ParseResult(
            status=ParseStatus.FAILED,
            reasons=[error],
            parser_used="none",
        )
        return deal
    
    def _extract_airports(self, text: str) -> list[str]:
        candidates = self.AIRPORT_PATTERN.findall(text)
        return [code for code in candidates if code in VALID_AIRPORT_CODES]
    
    def _city_to_airport(self, city: str) -> Optional[str]:
        if not city:
            return None
        city_lower = city.lower().strip()
        if city_lower in CITY_TO_AIRPORT:
            return CITY_TO_AIRPORT[city_lower]
        for city_name, code in CITY_TO_AIRPORT.items():
            if city_name in city_lower or city_lower in city_name:
                return code
        return None
    
    def _extract_price(self, text: str) -> Optional[tuple[int, str]]:
        match = self.PRICE_PATTERN.search(text)
        if match:
            price_str = match.group(1).replace(',', '').replace('.', '')
            try:
                price = int(price_str)
                currency = "USD"
                if '€' in text or 'EUR' in text.upper():
                    currency = "EUR"
                elif '£' in text or 'GBP' in text.upper():
                    currency = "GBP"
                elif 'NZD' in text.upper():
                    currency = "NZD"
                elif 'AUD' in text.upper():
                    currency = "AUD"
                return (price, currency)
            except ValueError:
                pass
        return None
