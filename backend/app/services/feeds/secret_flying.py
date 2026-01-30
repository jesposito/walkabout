import re
from typing import Optional
from app.models.deal import DealSource, ParseStatus
from app.services.feeds.base import BaseFeedParser, ParsedDeal, ParseResult


class SecretFlyingParser(BaseFeedParser):
    
    FEED_URL = "https://www.secretflying.com/feed/"
    
    HOTEL_KEYWORDS = ['hotel', 'per night', 'stars*', 'resort', 'hostel', 'accommodation']
    
    ROUTE_PATTERNS = [
        re.compile(r'Non-?stop\s+from\s+(?P<origin>[A-Za-z\s]+)\s+to\s+(?P<dest>[A-Za-z\s,]+?)(?:\s+(?:for|from|\())', re.IGNORECASE),
        re.compile(r'(?P<origin>[A-Za-z][A-Za-z\s]+?)\s+to\s+(?P<dest>[A-Za-z][A-Za-z\s,]+?)(?:\s+(?:for|from|only|\$|€|£|\())', re.IGNORECASE),
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
        title_lower = deal.raw_title.lower()
        
        if any(kw in title_lower for kw in self.HOTEL_KEYWORDS):
            return ParseResult(
                status=ParseStatus.FAILED,
                reasons=["Hotel deal, not a flight"],
                parser_used="regex_secret_flying",
            )
        
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
                
                if origin and dest and len(origin) > 1 and len(dest) > 1:
                    return (origin, dest)
        
        airports = self._extract_airports(title)
        if len(airports) >= 2:
            return (airports[0], airports[1])
        
        return (None, None)
    
    def _normalize_location(self, location: str) -> Optional[str]:
        # Strip common flight descriptors from start
        location = re.sub(r'^(Non-?stop\s+from\s+)', '', location, flags=re.IGNORECASE)
        location = re.sub(r'^(\d+-?stop\s+)', '', location, flags=re.IGNORECASE)  # "1-stop", "2-stop"
        # Strip trailing keywords
        location = re.sub(r'\s*(roundtrip|one-?way|nonstop|&\s*vice\s*versa).*$', '', location, flags=re.IGNORECASE)
        location = location.rstrip(',').strip()
        
        # Reject if just "Stop" or flight descriptors
        if location.lower() in ('stop', 'nonstop', 'non-stop', '1-stop', '2-stop', 'direct'):
            return None
        
        # Try to resolve to airport code
        code = self._city_to_airport(location)
        if code:
            return code
        
        # If it's already a 3-letter code, validate it
        if len(location) == 3 and location.isalpha():
            from app.services.feeds.base import VALID_AIRPORT_CODES
            if location.upper() in VALID_AIRPORT_CODES:
                return location.upper()
        
        return location
    
    def _extract_cabin_class(self, text: str) -> Optional[str]:
        for cabin, pattern in self.CABIN_PATTERNS.items():
            if pattern.search(text):
                return cabin
        return "economy"
