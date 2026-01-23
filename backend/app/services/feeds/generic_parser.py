import re
from typing import Optional
from dataclasses import dataclass
from app.models.deal import DealSource, ParseStatus
from app.services.feeds.base import BaseFeedParser, ParsedDeal, ParseResult


@dataclass
class FeedConfig:
    source: DealSource
    feed_url: str
    deal_keywords: list[str]
    skip_keywords: list[str]
    require_keywords: bool = False


FEED_CONFIGS: dict[DealSource, FeedConfig] = {
    DealSource.TPG: FeedConfig(
        source=DealSource.TPG,
        feed_url="https://thepointsguy.com/feed/",
        deal_keywords=['deal', 'fare', 'sale', 'cheap', 'price drop', 'award', 'miles'],
        skip_keywords=['review', 'credit card', 'hotel review', 'lounge'],
        require_keywords=True,
    ),
    DealSource.THE_FLIGHT_DEAL: FeedConfig(
        source=DealSource.THE_FLIGHT_DEAL,
        feed_url="https://www.theflightdeal.com/feed/",
        deal_keywords=['deal', 'fare', 'sale'],
        skip_keywords=[],
        require_keywords=False,
    ),
    DealSource.FLY4FREE: FeedConfig(
        source=DealSource.FLY4FREE,
        feed_url="https://www.fly4free.com/feed/",
        deal_keywords=['cheap', 'deal', 'from', 'error fare'],
        skip_keywords=['hotel', 'car rental'],
        require_keywords=False,
    ),
    DealSource.AFF: FeedConfig(
        source=DealSource.AFF,
        feed_url="https://www.australianfrequentflyer.com.au/feed/",
        deal_keywords=['deal', 'sale', 'fare', 'cheap', 'points', 'award'],
        skip_keywords=['review', 'lounge review', 'trip report'],
        require_keywords=False,
    ),
    DealSource.POINT_HACKS: FeedConfig(
        source=DealSource.POINT_HACKS,
        feed_url="https://www.pointhacks.com.au/feed/",
        deal_keywords=['deal', 'sale', 'bonus', 'points', 'cheap'],
        skip_keywords=['review', 'guide'],
        require_keywords=False,
    ),
    DealSource.HOLIDAY_PIRATES: FeedConfig(
        source=DealSource.HOLIDAY_PIRATES,
        feed_url="https://www.holidaypirates.com/feed",
        deal_keywords=['deal', 'cheap', 'from', 'flight'],
        skip_keywords=['hotel only'],
        require_keywords=False,
    ),
    DealSource.TRAVEL_FREE: FeedConfig(
        source=DealSource.TRAVEL_FREE,
        feed_url="https://travelfree.info/feed/",
        deal_keywords=['deal', 'cheap', 'error fare', 'mistake fare'],
        skip_keywords=[],
        require_keywords=False,
    ),
}


AIRLINES = [
    'United', 'American', 'Delta', 'Southwest', 'JetBlue', 'Alaska',
    'Air New Zealand', 'Qantas', 'Emirates', 'Singapore Airlines',
    'Cathay Pacific', 'British Airways', 'Lufthansa', 'Air France',
    'Qatar Airways', 'ANA', 'JAL', 'Korean Air', 'Fiji Airways',
    'Hawaiian', 'Virgin Atlantic', 'Virgin Australia', 'Air Canada',
    'Etihad', 'Thai Airways', 'Malaysia Airlines', 'KLM', 'Iberia',
    'Turkish Airlines', 'Swiss', 'Austrian', 'SAS', 'Finnair',
    'TAP Portugal', 'Aeromexico', 'LATAM', 'Avianca', 'Copa',
]


# Regex to match emoji and other non-ASCII symbols
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # misc
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U00002600-\U000026FF"  # misc symbols (sun, etc)
    "]+",
    flags=re.UNICODE
)


class GenericFeedParser(BaseFeedParser):
    
    # THE_FLIGHT_DEAL format: "Airline: City – City, Country. $Price"
    THE_FLIGHT_DEAL_PATTERN = re.compile(
        r'^[A-Za-z\s]+:\s*'                      # Airline:
        r'(?P<origin>[A-Za-z\s\.]+?)'            # Origin city
        r'\s*[-–—→]\s*'                          # Separator
        r'(?P<dest>[A-Za-z\s\.]+?)'              # Destination city
        r'(?:,\s*[A-Za-z\s]+)?'                  # Optional ", Country"
        r'(?:\s*\([^)]+\))?'                     # Optional "(and vice versa)"
        r'\s*\.',                                # Period before price
        re.IGNORECASE
    )
    
    # TRAVEL_FREE format: "Flights from City to DESTINATION for €Price"
    TRAVEL_FREE_PATTERN = re.compile(
        r'flights?\s+from\s+'
        r'(?P<origin>[A-Za-z\s]+?)'              # Origin city
        r'\s+to\s+'
        r'(?P<dest>[A-Za-z\s\(\)]+?)'            # Destination (may include country in parens)
        r'\s+(?:from|for)\s*[€£\$]',
        re.IGNORECASE
    )
    
    # Generic patterns as fallback
    ROUTE_PATTERNS = [
        # Direct airport codes: LAX – JFK, SFO-LHR
        re.compile(r'\b(?P<origin>[A-Z]{3})\s*[-–—→]+\s*(?P<dest>[A-Z]{3})\b'),
        # "from City to City for/from $"
        re.compile(r'from\s+(?P<origin>[A-Za-z\s]+?)\s+to\s+(?P<dest>[A-Za-z\s]+?)(?:\s+(?:from|for|starting|\$|€|£|\d))', re.IGNORECASE),
        # "City to City from/for $"
        re.compile(r'(?P<origin>[A-Za-z]+)\s+to\s+(?P<dest>[A-Za-z]+)\s+(?:from|for)\s+[\$€£]', re.IGNORECASE),
    ]
    
    def __init__(self, config: FeedConfig):
        super().__init__(config.feed_url, config.source)
        self.config = config
    
    def extract_deal_details(self, deal: ParsedDeal) -> ParseResult:
        title_lower = deal.raw_title.lower()
        
        if any(skip in title_lower for skip in self.config.skip_keywords):
            return ParseResult(
                status=ParseStatus.FAILED,
                reasons=["Skipped: contains skip keyword"],
                parser_used="generic",
            )
        
        if self.config.require_keywords:
            if not any(kw in title_lower for kw in self.config.deal_keywords):
                return ParseResult(
                    status=ParseStatus.FAILED,
                    reasons=["No deal keywords found"],
                    parser_used="generic",
                )
        
        text = f"{deal.raw_title} {deal.raw_summary or ''}"
        
        origin, destination = self._extract_route(deal.raw_title)
        price_info = self._extract_price(text)
        
        return ParseResult(
            origin=origin,
            destination=destination,
            price=price_info[0] if price_info else None,
            currency=price_info[1] if price_info else None,
            cabin_class=self._extract_cabin_class(text),
            airline=self._extract_airline(text),
            parser_used="generic",
        )
    
    def _extract_route(self, title: str) -> tuple[Optional[str], Optional[str]]:
        clean_title = EMOJI_PATTERN.sub(' ', title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        
        all_patterns = [
            self.THE_FLIGHT_DEAL_PATTERN,
            self.TRAVEL_FREE_PATTERN,
            *self.ROUTE_PATTERNS,
        ]
        
        for pattern in all_patterns:
            match = pattern.search(clean_title)
            if match:
                origin_raw = match.group('origin').strip()
                dest_raw = match.group('dest').strip()
                
                origin_raw = self._clean_location(origin_raw)
                dest_raw = self._clean_location(dest_raw)
                
                origin = self._resolve_location(origin_raw)
                dest = self._resolve_location(dest_raw)
                
                if origin and dest and origin != dest:
                    return (origin, dest)
        
        return (None, None)
    
    def _clean_location(self, location: str) -> str:
        location = re.sub(r'\([^)]*\)', '', location)
        location = re.sub(r',.*$', '', location)
        location = re.sub(r'\s*(and vice versa|roundtrip|one-way).*$', '', location, flags=re.IGNORECASE)
        return location.strip()
    
    def _resolve_location(self, location: str) -> Optional[str]:
        if not location:
            return None
        location = location.strip()
        upper = location.upper()
        if len(upper) == 3 and upper.isalpha():
            from app.services.feeds.base import VALID_AIRPORT_CODES
            if upper in VALID_AIRPORT_CODES:
                return upper
        code = self._city_to_airport(location)
        if code:
            return code
        return None
    
    def _normalize_location(self, location: str) -> Optional[str]:
        location = re.sub(r'^(\d+-?stop\s+)', '', location, flags=re.IGNORECASE)
        location = re.sub(r'\s*(roundtrip|one-?way|nonstop|deal|from|for).*$', '', location, flags=re.IGNORECASE)
        location = location.strip()
        
        if location.lower() in ('stop', 'nonstop', 'non-stop', '1-stop', '2-stop', 'direct'):
            return None
        
        location = location.upper()
        if len(location) == 3 and location.isalpha():
            return location
        return location[:20] if location else None
    
    def _extract_cabin_class(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        if 'first class' in text_lower or 'first-class' in text_lower:
            return "first"
        if 'business class' in text_lower or 'business-class' in text_lower:
            return "business"
        if 'premium economy' in text_lower:
            return "premium_economy"
        return "economy"
    
    def _extract_airline(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for airline in AIRLINES:
            if airline.lower() in text_lower:
                return airline
        return None


def create_parser(source: DealSource) -> Optional[GenericFeedParser]:
    config = FEED_CONFIGS.get(source)
    if config:
        return GenericFeedParser(config)
    return None
