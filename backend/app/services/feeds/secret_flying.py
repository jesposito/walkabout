import re
from typing import Optional
from app.models.deal import DealSource
from app.services.feeds.base import BaseFeedParser, ParsedDeal, ParseResult


class SecretFlyingParser(BaseFeedParser):
    
    FEED_URL = "https://www.secretflying.com/feed/"
    
    ROUTE_PATTERNS = [
        re.compile(r'(?P<origin>[A-Za-z\s]+)\s+to\s+(?P<dest>[A-Za-z\s]+)(?:\s+from)?', re.IGNORECASE),
        re.compile(r'(?P<origin>[A-Z]{3})\s*[-–]\s*(?P<dest>[A-Z]{3})', re.IGNORECASE),
    ]
    
    CABIN_PATTERNS = {
        'business': re.compile(r'business\s*class', re.IGNORECASE),
        'first': re.compile(r'first\s*class', re.IGNORECASE),
        'premium_economy': re.compile(r'premium\s*economy', re.IGNORECASE),
    }
    
    def __init__(self):
        super().__init__(self.FEED_URL, DealSource.SECRET_FLYING)
    
    def extract_deal_details(self, deal: ParsedDeal) -> ParseResult:
        text = f"{deal.raw_title} {deal.raw_summary or ''}"
        
        origin, destination = self._extract_route(deal.raw_title)
        
        price_info = self._extract_price(text)
        price = price_info[0] if price_info else None
        currency = price_info[1] if price_info else None
        
        cabin_class = self._extract_cabin_class(text)
        
        return ParseResult(
            origin=origin,
            destination=destination,
            price=price,
            currency=currency,
            cabin_class=cabin_class,
            parser_used="regex_secret_flying",
        )
    
    def _extract_route(self, title: str) -> tuple[Optional[str], Optional[str]]:
        for pattern in self.ROUTE_PATTERNS:
            match = pattern.search(title)
            if match:
                origin = match.group('origin').strip()
                dest = match.group('dest').strip()
                
                origin = self._normalize_location(origin)
                dest = self._normalize_location(dest)
                
                return (origin, dest)
        
        airports = self._extract_airports(title)
        if len(airports) >= 2:
            return (airports[0], airports[1])
        
        return (None, None)
    
    def _normalize_location(self, location: str) -> str:
        location = re.sub(r'\s*(from|roundtrip|one-?way|nonstop).*$', '', location, flags=re.IGNORECASE)
        return location.strip()
    
    def _extract_cabin_class(self, text: str) -> Optional[str]:
        for cabin, pattern in self.CABIN_PATTERNS.items():
            if pattern.search(text):
                return cabin
        return "economy"
