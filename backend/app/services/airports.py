from typing import Optional
from dataclasses import dataclass
from pathlib import Path
import csv
import math
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class Airport:
    code: str
    name: str
    city: str
    country: str
    region: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


AIRPORTS: dict[str, Airport] = {}
CITY_TO_CODES: dict[str, list[str]] = {}
COUNTRY_TO_CODES: dict[str, list[str]] = {}

REGION_MAP = {
    'africa': 'Africa',
    'antarctica': 'Antarctica', 
    'asia': 'Asia',
    'europe': 'Europe',
    'north america': 'North America',
    'oceania': 'Oceania',
    'south america': 'South America',
}

TIMEZONE_TO_REGION = {
    'Pacific/': 'Oceania',
    'Australia/': 'Oceania',
    'Asia/': 'Asia',
    'Europe/': 'Europe',
    'America/': 'North America',
    'Africa/': 'Africa',
    'Atlantic/': 'Europe',
    'Indian/': 'Africa',
}

COUNTRY_REGION_OVERRIDES = {
    'Brazil': 'South America',
    'Argentina': 'South America',
    'Chile': 'South America',
    'Peru': 'South America',
    'Colombia': 'South America',
    'Venezuela': 'South America',
    'Ecuador': 'South America',
    'Bolivia': 'South America',
    'Paraguay': 'South America',
    'Uruguay': 'South America',
    'Mexico': 'North America',
    'United States': 'North America',
    'Canada': 'North America',
}


def _infer_region(country: str, timezone: str) -> str:
    if country in COUNTRY_REGION_OVERRIDES:
        return COUNTRY_REGION_OVERRIDES[country]
    for tz_prefix, region in TIMEZONE_TO_REGION.items():
        if timezone.startswith(tz_prefix):
            return region
    return 'Unknown'


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two lat/long points."""
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


FALLBACK_AIRPORTS = [
    ('AKL', 'Auckland International', 'Auckland', 'New Zealand', 'Oceania'),
    ('WLG', 'Wellington International', 'Wellington', 'New Zealand', 'Oceania'),
    ('CHC', 'Christchurch International', 'Christchurch', 'New Zealand', 'Oceania'),
    ('SYD', 'Sydney', 'Sydney', 'Australia', 'Oceania'),
    ('MEL', 'Melbourne', 'Melbourne', 'Australia', 'Oceania'),
    ('BNE', 'Brisbane', 'Brisbane', 'Australia', 'Oceania'),
    ('NAN', 'Nadi', 'Nadi', 'Fiji', 'Oceania'),
    ('LAX', 'Los Angeles International', 'Los Angeles', 'United States', 'North America'),
    ('SFO', 'San Francisco International', 'San Francisco', 'United States', 'North America'),
    ('JFK', 'John F Kennedy', 'New York', 'United States', 'North America'),
    ('ORD', 'O\'Hare', 'Chicago', 'United States', 'North America'),
    ('DFW', 'Dallas Fort Worth', 'Dallas', 'United States', 'North America'),
    ('SEA', 'Seattle-Tacoma', 'Seattle', 'United States', 'North America'),
    ('MIA', 'Miami International', 'Miami', 'United States', 'North America'),
    ('BOS', 'Logan International', 'Boston', 'United States', 'North America'),
    ('DEN', 'Denver International', 'Denver', 'United States', 'North America'),
    ('ATL', 'Hartsfield-Jackson', 'Atlanta', 'United States', 'North America'),
    ('IAD', 'Dulles', 'Washington', 'United States', 'North America'),
    ('PDX', 'Portland International', 'Portland', 'United States', 'North America'),
    ('PHX', 'Phoenix Sky Harbor', 'Phoenix', 'United States', 'North America'),
    ('LAS', 'Harry Reid', 'Las Vegas', 'United States', 'North America'),
    ('HNL', 'Honolulu', 'Honolulu', 'United States', 'North America'),
    ('LHR', 'Heathrow', 'London', 'United Kingdom', 'Europe'),
    ('CDG', 'Charles de Gaulle', 'Paris', 'France', 'Europe'),
    ('AMS', 'Schiphol', 'Amsterdam', 'Netherlands', 'Europe'),
    ('FRA', 'Frankfurt', 'Frankfurt', 'Germany', 'Europe'),
    ('FCO', 'Fiumicino', 'Rome', 'Italy', 'Europe'),
    ('MXP', 'Malpensa', 'Milan', 'Italy', 'Europe'),
    ('MAD', 'Barajas', 'Madrid', 'Spain', 'Europe'),
    ('BCN', 'El Prat', 'Barcelona', 'Spain', 'Europe'),
    ('DXB', 'Dubai International', 'Dubai', 'United Arab Emirates', 'Asia'),
    ('SIN', 'Changi', 'Singapore', 'Singapore', 'Asia'),
    ('HKG', 'Hong Kong', 'Hong Kong', 'Hong Kong', 'Asia'),
    ('NRT', 'Narita', 'Tokyo', 'Japan', 'Asia'),
    ('ICN', 'Incheon', 'Seoul', 'South Korea', 'Asia'),
    ('BKK', 'Suvarnabhumi', 'Bangkok', 'Thailand', 'Asia'),
    ('MNL', 'Ninoy Aquino', 'Manila', 'Philippines', 'Asia'),
    ('SXM', 'Princess Juliana', 'St Maarten', 'Sint Maarten', 'North America'),
    ('SJU', 'Luis Munoz Marin', 'San Juan', 'Puerto Rico', 'North America'),
    ('LIH', 'Lihue', 'Kauai', 'United States', 'North America'),
    ('GYE', 'Jose Joaquin de Olmedo', 'Guayaquil', 'Ecuador', 'South America'),
]


def _load_fallback():
    global AIRPORTS, CITY_TO_CODES, COUNTRY_TO_CODES
    for code, name, city, country, region in FALLBACK_AIRPORTS:
        airport = Airport(code=code, name=name, city=city, country=country, region=region)
        AIRPORTS[code] = airport
        city_lower = city.lower()
        if city_lower not in CITY_TO_CODES:
            CITY_TO_CODES[city_lower] = []
        if code not in CITY_TO_CODES[city_lower]:
            CITY_TO_CODES[city_lower].append(code)
    logger.info(f"Loaded {len(FALLBACK_AIRPORTS)} fallback airports")


def _load_airports():
    global AIRPORTS, CITY_TO_CODES, COUNTRY_TO_CODES
    
    data_file = Path(__file__).parent.parent / 'resources' / 'airports.dat'
    if not data_file.exists():
        logger.warning(f"Airport data file not found: {data_file}, using fallback")
        _load_fallback()
        return
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 12:
                    continue
                
                iata_code = row[4].strip()
                if not iata_code or iata_code == '\\N' or len(iata_code) != 3:
                    continue
                
                name = row[1].strip()
                city = row[2].strip()
                country = row[3].strip()
                timezone = row[11].strip() if len(row) > 11 else ''
                
                region = _infer_region(country, timezone)

                lat = None
                lon = None
                try:
                    lat = float(row[6])
                    lon = float(row[7])
                except (ValueError, IndexError):
                    pass

                airport = Airport(
                    code=iata_code,
                    name=name,
                    city=city,
                    country=country,
                    region=region,
                    latitude=lat,
                    longitude=lon,
                )
                
                AIRPORTS[iata_code] = airport
                
                city_lower = city.lower()
                if city_lower not in CITY_TO_CODES:
                    CITY_TO_CODES[city_lower] = []
                if iata_code not in CITY_TO_CODES[city_lower]:
                    CITY_TO_CODES[city_lower].append(iata_code)
                
                country_lower = country.lower()
                if country_lower not in COUNTRY_TO_CODES:
                    COUNTRY_TO_CODES[country_lower] = []
                if iata_code not in COUNTRY_TO_CODES[country_lower]:
                    COUNTRY_TO_CODES[country_lower].append(iata_code)
        
        if len(AIRPORTS) == 0:
            raise ValueError("No airports loaded from file")
            
        logger.info(f"Loaded {len(AIRPORTS)} airports from {data_file}")
        
    except Exception as e:
        logger.error(f"Error loading airports from {data_file}: {e}, using fallback")
        AIRPORTS.clear()
        CITY_TO_CODES.clear()
        COUNTRY_TO_CODES.clear()
        _load_fallback()


_load_airports()

CITY_ALIASES = {
    'nyc': 'new york',
    'la': 'los angeles',
    'los angeles': 'los angeles',
    'sf': 'san francisco',
    'dc': 'washington',
    'vegas': 'las vegas',
    'philly': 'philadelphia',
    'chi-town': 'chicago',
    'hawaii': 'honolulu',
    'bali': 'denpasar',
    'phuket': 'phuket',
    'fiji': 'nadi',
    'tahiti': 'papeete',
    'cook islands': 'rarotonga',
    'raro': 'rarotonga',
    'maldives': 'male',
    'mauritius': 'port louis',
    'seychelles': 'mahe island',
    'kauai': 'lihue',
    'maui': 'kahului',
    'st. maarten': 'philipsburg',
    'st maarten': 'philipsburg',
    'puerto rico': 'san juan',
    'vietnam': 'ho chi minh city',
    'sri lanka': 'colombo',
    'thailand': 'bangkok',
    'indonesia': 'jakarta',
    'philippines': 'manila',
    'japan': 'tokyo',
    'brazil': 'sao paulo',
    'india': 'delhi',
    'california': 'los angeles',
    'sun coast': 'sunshine coast',
    'suncoast': 'sunshine coast',
    'sunny coast': 'sunshine coast',
    'goldie': 'gold coast',
    'gc': 'gold coast',
    'kl': 'kuala lumpur',
    'hk': 'hong kong',
    'sg': 'singapore',
    'mel': 'melbourne',
    'syd': 'sydney',
    'bne': 'brisbane',
    'per': 'perth',
    'akl': 'auckland',
    'wlg': 'wellington',
    'chc': 'christchurch',
    'zqn': 'queenstown',
    'china': 'shanghai',
    'korea': 'seoul',
    'europe': 'london',
    'uk': 'london',
    'usa': 'los angeles',
    'america': 'los angeles',
}

PREFERRED_AIRPORT = {
    'sydney': 'SYD',
    'melbourne': 'MEL',
    'perth': 'PER',
    'brisbane': 'BNE',
    'adelaide': 'ADL',
    'cairns': 'CNS',
    'gold coast': 'OOL',
    'darwin': 'DRW',
    'hobart': 'HBA',
    'auckland': 'AKL',
    'wellington': 'WLG',
    'christchurch': 'CHC',
    'queenstown': 'ZQN',
    'dunedin': 'DUD',
    'hamilton': 'HLZ',
    'napier': 'NPE',
    'new york': 'JFK',
    'london': 'LHR',
    'paris': 'CDG',
    'tokyo': 'NRT',
    'osaka': 'KIX',
    'seoul': 'ICN',
    'shanghai': 'PVG',
    'beijing': 'PEK',
    'guangzhou': 'CAN',
    'shenzhen': 'SZX',
    'taipei': 'TPE',
    'washington': 'IAD',
    'chicago': 'ORD',
    'los angeles': 'LAX',
    'milan': 'MXP',
    'rome': 'FCO',
    'moscow': 'SVO',
    'sao paulo': 'GRU',
    'buenos aires': 'EZE',
    'bangkok': 'BKK',
    'kuala lumpur': 'KUL',
    'jakarta': 'CGK',
    'denpasar': 'DPS',
    'delhi': 'DEL',
    'mumbai': 'BOM',
    'nairobi': 'NBO',
    'dallas': 'DFW',
    'houston': 'IAH',
    'san juan': 'SJU',
    'lihue': 'LIH',
    'kahului': 'OGG',
    'philipsburg': 'SXM',
    'denver': 'DEN',
    'phoenix': 'PHX',
    'seattle': 'SEA',
    'portland': 'PDX',
    'miami': 'MIA',
    'atlanta': 'ATL',
    'boston': 'BOS',
    'detroit': 'DTW',
    'minneapolis': 'MSP',
    'san francisco': 'SFO',
    'honolulu': 'HNL',
    'singapore': 'SIN',
    'hong kong': 'HKG',
    'dubai': 'DXB',
    'doha': 'DOH',
    'vancouver': 'YVR',
    'toronto': 'YYZ',
    'amsterdam': 'AMS',
    'frankfurt': 'FRA',
    'munich': 'MUC',
    'zurich': 'ZRH',
    'madrid': 'MAD',
    'barcelona': 'BCN',
    'lisbon': 'LIS',
    'dublin': 'DUB',
    'manchester': 'MAN',
    'nadi': 'NAN',
    'rarotonga': 'RAR',
    'papeete': 'PPT',
    'apia': 'APW',
    'sunshine coast': 'MCY',
    'canberra': 'CBR',
    'newcastle': 'NTL',
    'townsville': 'TSV',
    'launceston': 'LST',
    'hamilton island': 'HTI',
    'palmerston north': 'PMR',
    'rotorua': 'ROT',
    'nelson': 'NSN',
    'invercargill': 'IVC',
}

SKIP_WORDS = {
    'stop', 'stops', 'nonstop', 'non-stop', 'direct', 
    'one', 'two', 'the', 'for', 'from', 'and', 'via',
    'roundtrip', 'round-trip', 'one-way', 'oneway',
    'deal', 'deals', 'sale', 'cheap', 'flight', 'flights',
    'air', 'airlines', 'airways',
}


class AirportLookup:
    
    _word_pattern = re.compile(r'\b([A-Za-z][A-Za-z\s\.\-\']+)\b')
    _code_pattern = re.compile(r'\b([A-Z]{3})\b')
    
    @classmethod
    def find_locations(cls, text: str) -> list[tuple[str, int, str]]:
        """
        Find airport codes and city names in text.
        Returns list of (code, position, match_type) tuples.
        match_type is 'code' for direct IATA matches, 'city' for city name matches.
        """
        results = []
        text_lower = text.lower()
        
        for match in cls._code_pattern.finditer(text):
            code = match.group(1)
            if code in AIRPORTS:
                word_before = text[max(0, match.start()-10):match.start()].lower()
                if not any(skip in word_before for skip in ['http', 'www', '://']):
                    results.append((code, match.start(), 'code'))
        
        checked_positions = set()
        
        all_cities = list(CITY_TO_CODES.keys()) + list(CITY_ALIASES.keys())
        all_cities.sort(key=len, reverse=True)
        
        for city in all_cities:
            if len(city) < 3:
                continue
            
            pattern = r'\b' + re.escape(city) + r'\b'
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                pos = match.start()
                
                if any(abs(pos - p) < 3 for p in checked_positions):
                    continue
                
                if city in SKIP_WORDS:
                    continue
                
                resolved_city = CITY_ALIASES.get(city, city)
                
                if resolved_city in PREFERRED_AIRPORT:
                    code = PREFERRED_AIRPORT[resolved_city]
                elif resolved_city in CITY_TO_CODES:
                    code = CITY_TO_CODES[resolved_city][0]
                else:
                    continue
                
                results.append((code, pos, 'city'))
                checked_positions.add(pos)
        
        results.sort(key=lambda x: x[1])
        return results
    
    @classmethod
    def extract_route(cls, text: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extract origin and destination from text.
        Only returns a route when there's structural evidence (separators, to/from patterns).
        Returns (None, None) for city lists or incidental mentions.
        """
        raw_locations = cls.find_locations(text)

        if len(raw_locations) < 2:
            return (None, None)

        # Deduplicate: same code at same position can appear as both 'code' and 'city'
        seen = set()
        locations = []
        for code, pos, match_type in raw_locations:
            key = (code, pos)
            if key not in seen:
                seen.add(key)
                locations.append((code, pos, match_type))

        if len(locations) < 2:
            return (None, None)

        # Count unique airport codes (not positions)
        unique_codes = set(code for code, _, _ in locations)

        # City lists: 4+ unique locations is almost certainly a list, not a route
        if len(unique_codes) >= 4:
            return (None, None)

        # 3+ unique locations with commas between them is a list
        if len(unique_codes) >= 3:
            span = text[locations[0][1]:locations[-1][1] + 10]
            if span.count(',') >= 2:
                return (None, None)

        text_lower = text.lower()

        # Strategy 1: Strong separators (unambiguous route indicators)
        for sep in ['–', '—', '→']:
            pos = text.find(sep)
            if pos > 0:
                before = [(code, p, t) for code, p, t in locations if p < pos]
                after = [(code, p, t) for code, p, t in locations if p > pos]
                if before and after:
                    origin = before[-1][0]
                    dest = after[0][0]
                    if origin != dest:
                        return (origin, dest)

        # Strategy 2: "to" keyword between locations
        for to_match in re.finditer(r'\bto\b', text_lower):
            to_pos = to_match.start()
            before = [(code, p, t) for code, p, t in locations if p < to_pos]
            after = [(code, p, t) for code, p, t in locations if p > to_match.end()]
            if before and after:
                origin = before[-1][0]
                dest = after[0][0]
                if origin != dest:
                    return (origin, dest)

        # Strategy 3: "from ORIGIN" with destination mentioned earlier
        # Handles "Tokyo from Auckland $599" → origin=AKL, dest=NRT
        from_match = re.search(r'\bfrom\s+', text_lower)
        if from_match:
            from_pos = from_match.end()
            before_from = [(code, p, t) for code, p, t in locations if p < from_match.start()]
            after_from = [(code, p, t) for code, p, t in locations if p >= from_pos]

            if before_from and after_from:
                destination = before_from[-1][0]
                origin = after_from[0][0]
                if origin != destination:
                    return (origin, destination)

        # Strategy 4: CODE-CODE pattern with hyphen (e.g., "AKL-SYD", "AKL - SYD")
        # Only for explicit IATA code pairs, not general hyphens in titles
        code_dash = re.search(r'\b([A-Z]{3})\s*-\s*([A-Z]{3})\b', text)
        if code_dash:
            c1, c2 = code_dash.group(1), code_dash.group(2)
            if c1 in AIRPORTS and c2 in AIRPORTS and c1 != c2:
                return (c1, c2)

        # No structural route evidence found — don't guess from incidental mentions
        return (None, None)


class AirportService:
    
    @staticmethod
    def is_valid(code: str) -> bool:
        if not code or len(code) != 3:
            return False
        return code.upper() in AIRPORTS
    
    @staticmethod
    def validate(code: str) -> tuple[bool, Optional[str]]:
        if not code:
            return False, "Airport code is required"
        
        code = code.strip().upper()
        
        if len(code) != 3:
            return False, f"Airport code must be 3 characters, got '{code}'"
        
        if not code.isalpha():
            return False, f"Airport code must contain only letters, got '{code}'"
        
        if code in AIRPORTS:
            return True, None
        
        suggestions = AirportService.search(code, limit=3)
        if suggestions:
            suggestion_text = ", ".join([f"{s.code} ({s.city})" for s in suggestions])
            return False, f"Unknown airport code '{code}'. Did you mean: {suggestion_text}?"
        
        return False, f"Unknown airport code '{code}'. Check that it's a valid IATA code."
    
    @staticmethod
    def search(query: str, limit: int = 10) -> list[Airport]:
        if not query or len(query) < 2:
            return []
        
        query_lower = query.lower().strip()
        results = []
        
        if len(query) == 3 and query.upper() in AIRPORTS:
            return [AIRPORTS[query.upper()]]
        
        for code, airport in AIRPORTS.items():
            score = 0
            
            if code.lower() == query_lower:
                score = 100
            elif code.lower().startswith(query_lower):
                score = 90
            elif query_lower in airport.city.lower():
                if airport.city.lower().startswith(query_lower):
                    score = 85
                else:
                    score = 70
            elif query_lower in airport.country.lower():
                score = 50
            elif query_lower in airport.name.lower():
                score = 40
            elif query_lower in airport.region.lower():
                score = 30
            
            if score > 0:
                results.append((score, airport))
        
        results.sort(key=lambda x: (-x[0], x[1].city))
        return [airport for _, airport in results[:limit]]
    
    @staticmethod
    def get(code: str) -> Optional[Airport]:
        return AIRPORTS.get(code.upper())
    
    @staticmethod
    def get_by_region(region: str) -> list[Airport]:
        return [a for a in AIRPORTS.values() if a.region.lower() == region.lower()]
    
    @staticmethod
    def get_by_country(country: str) -> list[Airport]:
        return [a for a in AIRPORTS.values() if a.country.lower() == country.lower()]
    
    @staticmethod
    def get_nearby_airports(code: str, radius_km: float = 500) -> list[tuple['Airport', float]]:
        """Get airports within radius_km of the given airport code.
        Returns list of (Airport, distance_km) tuples sorted by distance."""
        origin = AIRPORTS.get(code.upper())
        if not origin or origin.latitude is None or origin.longitude is None:
            return []

        results = []
        for apt in AIRPORTS.values():
            if apt.code == origin.code:
                continue
            if apt.latitude is None or apt.longitude is None:
                continue
            dist = _haversine(origin.latitude, origin.longitude, apt.latitude, apt.longitude)
            if dist <= radius_km:
                results.append((apt, dist))

        results.sort(key=lambda x: x[1])
        return results

    @staticmethod
    def get_country_for_airport(code: str) -> Optional[str]:
        """Get the country for an airport code."""
        apt = AIRPORTS.get(code.upper())
        return apt.country if apt else None

    @staticmethod
    def code_for_city(city: str) -> Optional[str]:
        city_lower = city.lower().strip()
        city_lower = re.sub(r'[.]', '', city_lower)
        
        if city_lower in CITY_ALIASES:
            city_lower = CITY_ALIASES[city_lower]
        
        if city_lower in PREFERRED_AIRPORT:
            return PREFERRED_AIRPORT[city_lower]
        
        if city_lower in CITY_TO_CODES:
            return CITY_TO_CODES[city_lower][0]
        
        for city_name in CITY_TO_CODES:
            if city_name in city_lower or city_lower in city_name:
                return CITY_TO_CODES[city_name][0]
        
        return None
