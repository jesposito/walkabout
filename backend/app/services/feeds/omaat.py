import re
from typing import Optional
from app.models.deal import DealSource, ParseStatus
from app.services.feeds.base import BaseFeedParser, ParsedDeal, ParseResult


class OMAATParser(BaseFeedParser):
    
    FEED_URL = "https://onemileatatime.com/feed/"
    
    DEAL_KEYWORDS = ['deal', 'fare', 'sale', 'cheap', 'discount', 'offer', 'price']
    SKIP_KEYWORDS = ['review', 'trip report', 'lounge', 'hotel review', 'question']
    
    ROUTE_PATTERNS = [
        re.compile(r'(?P<origin>[A-Za-z][A-Za-z\s,]+?)\s+to\s+(?P<dest>[A-Za-z][A-Za-z\s,]+?)(?:\s+(?:from|for|starting|only|\$|€|£))', re.IGNORECASE),
        re.compile(r'[\$€£]\s*\d+.*?(?P<origin>[A-Za-z\s]+)\s+to\s+(?P<dest>[A-Za-z\s]+)', re.IGNORECASE),
    ]
    
    AIRLINES = [
        'United', 'American', 'Delta', 'Southwest', 'JetBlue', 'Alaska',
        'Air New Zealand', 'Qantas', 'Emirates', 'Singapore Airlines',
        'Cathay Pacific', 'British Airways', 'Lufthansa', 'Air France',
        'Qatar Airways', 'ANA', 'JAL', 'Korean Air', 'Fiji Airways',
        'Hawaiian', 'Virgin Atlantic', 'Virgin Australia', 'Air Canada',
    ]
    
    def __init__(self):
        super().__init__(self.FEED_URL, DealSource.OMAAT)
    
    def extract_deal_details(self, deal: ParsedDeal) -> ParseResult:
        title_lower = deal.raw_title.lower()
        
        if any(skip in title_lower for skip in self.SKIP_KEYWORDS):
            return ParseResult(
                status=ParseStatus.FAILED,
                reasons=["Not a deal post"],
                parser_used="regex_omaat",
            )
        
        is_deal = any(kw in title_lower for kw in self.DEAL_KEYWORDS)
        has_price = bool(re.search(r'[\$€£]\s*\d+', deal.raw_title))
        
        if not is_deal and not has_price:
            return ParseResult(
                status=ParseStatus.FAILED,
                reasons=["No deal indicators found"],
                parser_used="regex_omaat",
            )
        
        text = f"{deal.raw_title} {deal.raw_summary or ''}"
        
        origin, destination = self._extract_route(deal.raw_title)
        
        price_info = self._extract_price(text)
        price = price_info[0] if price_info else None
        currency = price_info[1] if price_info else None
        
        cabin_class = self._extract_cabin_class(text)
        airline = self._extract_airline(text)
        
        return ParseResult(
            origin=origin,
            destination=destination,
            price=price,
            currency=currency,
            cabin_class=cabin_class,
            airline=airline,
            parser_used="regex_omaat",
        )
    
    def _extract_route(self, title: str) -> tuple[Optional[str], Optional[str]]:
        for pattern in self.ROUTE_PATTERNS:
            match = pattern.search(title)
            if match:
                origin = match.group('origin').strip()
                dest = match.group('dest').strip()
                
                origin = self._clean_location(origin)
                dest = self._clean_location(dest)
                
                if origin and dest and len(origin) > 1 and len(dest) > 1:
                    return (origin, dest)
        
        airports = self._extract_airports(title)
        if len(airports) >= 2:
            return (airports[0], airports[1])
        
        return (None, None)
    
    def _clean_location(self, location: str) -> str:
        location = re.sub(r'\s*(roundtrip|one-?way|nonstop|deal|alert|fare).*$', '', location, flags=re.IGNORECASE)
        location = location.rstrip(',').strip()
        return location
    
    def _extract_cabin_class(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if 'business' in text_lower:
            return "business"
        if 'first class' in text_lower:
            return "first"
        if 'premium economy' in text_lower:
            return "premium_economy"
        return "economy"
    
    def _extract_airline(self, text: str) -> Optional[str]:
        for airline in self.AIRLINES:
            if airline.lower() in text.lower():
                return airline
        return None
