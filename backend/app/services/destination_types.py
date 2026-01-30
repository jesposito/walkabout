from typing import Optional


DESTINATION_TYPES = {
    "tropical": {
        "name": "Tropical Beach",
        "emoji": "🏝️",
        "description": "Sun, sand, and palm trees",
        "airports": {"NAN", "RAR", "PPT", "DPS", "HKT", "MLE", "MRU", "CEB", "HNL", "OGG", "FJD"},
        "keywords": ["fiji", "tahiti", "bali", "phuket", "maldives", "hawaii", "beach", "island", "tropical"],
    },
    "pacific_islands": {
        "name": "Pacific Islands",
        "emoji": "🌺",
        "description": "Fiji, Cook Islands, Samoa, and more",
        "airports": {"NAN", "SUV", "RAR", "APW", "TBU", "VLI", "NOU", "PPT"},
        "keywords": ["fiji", "cook islands", "samoa", "tonga", "vanuatu", "tahiti", "pacific"],
    },
    "australia": {
        "name": "Australia",
        "emoji": "🦘",
        "description": "Cities, beaches, and outback",
        "airports": {"SYD", "MEL", "BNE", "PER", "ADL", "CBR", "OOL", "CNS", "HBA"},
        "keywords": ["sydney", "melbourne", "brisbane", "australia", "gold coast", "cairns"],
    },
    "japan": {
        "name": "Japan",
        "emoji": "🗾",
        "description": "Culture, food, and scenery",
        "airports": {"NRT", "HND", "KIX", "NGO", "FUK", "CTS", "OKA"},
        "keywords": ["tokyo", "osaka", "japan", "kyoto", "japanese"],
    },
    "southeast_asia": {
        "name": "Southeast Asia",
        "emoji": "🛕",
        "description": "Thailand, Vietnam, Singapore, and more",
        "airports": {"BKK", "HKT", "SIN", "KUL", "SGN", "HAN", "DAD", "MNL", "CEB", "DPS"},
        "keywords": ["thailand", "vietnam", "singapore", "bali", "malaysia", "philippines", "bangkok", "phuket"],
    },
    "europe": {
        "name": "Europe",
        "emoji": "🏰",
        "description": "History, culture, and cuisine",
        "airports": {"LHR", "CDG", "AMS", "FRA", "FCO", "BCN", "MAD", "LIS", "ATH", "VIE", "ZRH", "MUC"},
        "keywords": ["london", "paris", "rome", "barcelona", "amsterdam", "europe", "european"],
    },
    "uk": {
        "name": "United Kingdom",
        "emoji": "🇬🇧",
        "description": "London and beyond",
        "airports": {"LHR", "LGW", "STN", "MAN", "EDI"},
        "keywords": ["london", "uk", "britain", "england", "scotland"],
    },
    "usa_west": {
        "name": "US West Coast",
        "emoji": "🌉",
        "description": "California, Pacific Northwest",
        "airports": {"LAX", "SFO", "SEA", "PDX", "SAN", "LAS"},
        "keywords": ["los angeles", "san francisco", "seattle", "las vegas", "california"],
    },
    "usa_east": {
        "name": "US East Coast",
        "emoji": "🗽",
        "description": "New York, Florida, and more",
        "airports": {"JFK", "EWR", "BOS", "MIA", "FLL", "DCA", "IAD"},
        "keywords": ["new york", "miami", "boston", "florida", "washington"],
    },
    "hawaii": {
        "name": "Hawaii",
        "emoji": "🌴",
        "description": "Aloha paradise",
        "airports": {"HNL", "OGG", "LIH", "KOA"},
        "keywords": ["hawaii", "honolulu", "maui", "waikiki", "oahu"],
    },
    "family": {
        "name": "Family Friendly",
        "emoji": "👨‍👩‍👧‍👦",
        "description": "Great for kids and families",
        "airports": {"SYD", "MEL", "OOL", "NAN", "RAR", "HNL", "SIN", "HKG"},
        "keywords": ["family", "kids", "theme park", "resort"],
    },
    "adventure": {
        "name": "Adventure",
        "emoji": "🏔️",
        "description": "Hiking, diving, exploration",
        "airports": {"ZQN", "CHC", "CNS", "DPS", "RAR", "VLI", "KEF"},
        "keywords": ["adventure", "hiking", "diving", "trekking", "extreme"],
    },
    "city_break": {
        "name": "City Break",
        "emoji": "🌆",
        "description": "Shopping, dining, nightlife",
        "airports": {"SYD", "MEL", "SIN", "HKG", "TYO", "LHR", "JFK", "LAX"},
        "keywords": ["city", "shopping", "urban", "nightlife"],
    },
    "honeymoon": {
        "name": "Romantic/Honeymoon",
        "emoji": "💑",
        "description": "Couples getaways",
        "airports": {"MLE", "PPT", "NAN", "RAR", "DPS", "MRU", "FCO", "BCN"},
        "keywords": ["romantic", "honeymoon", "couples", "luxury"],
    },
}


class DestinationTypeService:
    
    @staticmethod
    def get_all_types() -> list[dict]:
        return [
            {
                "id": type_id,
                "name": data["name"],
                "emoji": data["emoji"],
                "description": data["description"],
            }
            for type_id, data in DESTINATION_TYPES.items()
        ]
    
    @staticmethod
    def get_airports_for_types(type_ids: list[str]) -> set[str]:
        airports = set()
        for type_id in type_ids:
            if type_id in DESTINATION_TYPES:
                airports.update(DESTINATION_TYPES[type_id]["airports"])
        return airports
    
    @staticmethod
    def get_keywords_for_types(type_ids: list[str]) -> set[str]:
        keywords = set()
        for type_id in type_ids:
            if type_id in DESTINATION_TYPES:
                keywords.update(DESTINATION_TYPES[type_id]["keywords"])
        return keywords
    
    @staticmethod
    def match_deal_to_types(
        destination: Optional[str],
        title: str,
        type_ids: list[str],
    ) -> bool:
        if not type_ids:
            return True
        
        dest_upper = (destination or "").upper()
        title_lower = title.lower()
        
        airports = DestinationTypeService.get_airports_for_types(type_ids)
        if dest_upper in airports:
            return True
        
        keywords = DestinationTypeService.get_keywords_for_types(type_ids)
        for keyword in keywords:
            if keyword in title_lower:
                return True
        
        return False
