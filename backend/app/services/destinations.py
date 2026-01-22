"""
Similar Destinations Service

Maps destinations to groups and provides alternatives.
"You want Fiji? Rarotonga is 40% cheaper right now."
"""

from typing import Optional


# Destination groups with their member airports
DESTINATION_GROUPS = {
    "south_pacific_islands": {
        "name": "South Pacific Islands",
        "airports": {"NAN", "SUV", "RAR", "APW", "PPT", "TBU", "VLI", "NOU", "IUE", "WLS"},
        "keywords": ["fiji", "rarotonga", "samoa", "tahiti", "tonga", "vanuatu", "new caledonia", "cook islands", "niue"],
    },
    "australia_east": {
        "name": "Australia East Coast",
        "airports": {"SYD", "MEL", "BNE", "OOL", "CNS", "CBR"},
        "keywords": ["sydney", "melbourne", "brisbane", "gold coast", "cairns", "canberra"],
    },
    "australia_other": {
        "name": "Australia Other",
        "airports": {"PER", "ADL", "HBA", "DRW"},
        "keywords": ["perth", "adelaide", "hobart", "darwin", "tasmania"],
    },
    "hawaii": {
        "name": "Hawaii",
        "airports": {"HNL", "OGG", "LIH", "KOA", "ITO"},
        "keywords": ["hawaii", "honolulu", "maui", "kauai", "oahu", "big island"],
    },
    "japan": {
        "name": "Japan",
        "airports": {"NRT", "HND", "KIX", "NGO", "FUK", "CTS", "OKA"},
        "keywords": ["tokyo", "osaka", "japan", "kyoto", "fukuoka", "sapporo", "okinawa"],
    },
    "korea": {
        "name": "South Korea",
        "airports": {"ICN", "GMP", "PUS"},
        "keywords": ["seoul", "korea", "busan"],
    },
    "southeast_asia_beach": {
        "name": "Southeast Asia (Beach)",
        "airports": {"DPS", "HKT", "KUL", "BKK", "SGN", "DAD", "CEB"},
        "keywords": ["bali", "phuket", "thailand", "vietnam", "philippines", "danang"],
    },
    "southeast_asia_city": {
        "name": "Southeast Asia (City)",
        "airports": {"SIN", "BKK", "KUL", "HAN", "SGN", "MNL"},
        "keywords": ["singapore", "bangkok", "kuala lumpur", "hanoi", "ho chi minh", "manila"],
    },
    "china_hk_taiwan": {
        "name": "Greater China",
        "airports": {"HKG", "TPE", "PVG", "PEK", "CAN"},
        "keywords": ["hong kong", "taiwan", "taipei", "shanghai", "beijing", "guangzhou", "china"],
    },
    "usa_west_coast": {
        "name": "US West Coast",
        "airports": {"LAX", "SFO", "SEA", "PDX", "SAN", "LAS"},
        "keywords": ["los angeles", "san francisco", "seattle", "las vegas", "portland", "san diego", "california"],
    },
    "usa_east_coast": {
        "name": "US East Coast",
        "airports": {"JFK", "EWR", "BOS", "DCA", "IAD", "MIA", "FLL"},
        "keywords": ["new york", "boston", "washington", "miami", "florida"],
    },
    "europe_western": {
        "name": "Western Europe",
        "airports": {"LHR", "LGW", "CDG", "AMS", "FRA", "ZRH", "BRU"},
        "keywords": ["london", "paris", "amsterdam", "frankfurt", "zurich", "brussels", "uk", "france", "germany"],
    },
    "europe_southern": {
        "name": "Southern Europe",
        "airports": {"FCO", "BCN", "MAD", "LIS", "ATH"},
        "keywords": ["rome", "barcelona", "madrid", "lisbon", "athens", "italy", "spain", "portugal", "greece"],
    },
}

# Map airport to its group(s)
AIRPORT_TO_GROUPS: dict[str, list[str]] = {}
for group_id, group_data in DESTINATION_GROUPS.items():
    for airport in group_data["airports"]:
        if airport not in AIRPORT_TO_GROUPS:
            AIRPORT_TO_GROUPS[airport] = []
        AIRPORT_TO_GROUPS[airport].append(group_id)


class DestinationService:
    """Service for finding similar/alternative destinations."""
    
    @staticmethod
    def get_groups_for_airport(airport: str) -> list[str]:
        """Get all destination groups an airport belongs to."""
        return AIRPORT_TO_GROUPS.get(airport.upper(), [])
    
    @staticmethod
    def get_similar_airports(airport: str) -> set[str]:
        """Get airports similar to the given one (in same groups)."""
        groups = DestinationService.get_groups_for_airport(airport)
        similar = set()
        for group_id in groups:
            group = DESTINATION_GROUPS.get(group_id)
            if group:
                similar.update(group["airports"])
        # Remove the original airport
        similar.discard(airport.upper())
        return similar
    
    @staticmethod
    def get_group_for_keyword(keyword: str) -> Optional[str]:
        """Find which destination group a keyword belongs to."""
        keyword_lower = keyword.lower()
        for group_id, group_data in DESTINATION_GROUPS.items():
            if keyword_lower in group_data["keywords"]:
                return group_id
        return None
    
    @staticmethod
    def get_group_name(group_id: str) -> Optional[str]:
        """Get human-readable name for a group."""
        group = DESTINATION_GROUPS.get(group_id)
        return group["name"] if group else None
    
    @staticmethod
    def expand_watched_destinations(watched: list[str]) -> dict[str, set[str]]:
        """
        Expand a list of watched destinations to include similar airports.
        Returns dict mapping original -> set of similar airports.
        """
        expanded = {}
        for dest in watched:
            dest_upper = dest.upper()
            similar = DestinationService.get_similar_airports(dest_upper)
            if similar:
                expanded[dest_upper] = similar
        return expanded
    
    @staticmethod
    def is_similar_destination(
        deal_dest: str, 
        watched_destinations: list[str]
    ) -> Optional[tuple[str, str, str]]:
        """
        Check if a deal destination is similar to any watched destination.
        
        Returns:
            Tuple of (watched_dest, group_name, deal_dest) if similar, None otherwise.
        """
        if not deal_dest:
            return None
            
        deal_dest_upper = deal_dest.upper()
        
        # Direct match not considered "similar" (that's exact)
        if deal_dest_upper in [d.upper() for d in watched_destinations]:
            return None
        
        # Check if deal dest is in a group with any watched dest
        deal_groups = DestinationService.get_groups_for_airport(deal_dest_upper)
        
        for watched in watched_destinations:
            watched_upper = watched.upper()
            watched_groups = DestinationService.get_groups_for_airport(watched_upper)
            
            # Find common groups
            common_groups = set(deal_groups) & set(watched_groups)
            if common_groups:
                group_id = list(common_groups)[0]
                group_name = DestinationService.get_group_name(group_id)
                return (watched_upper, group_name, deal_dest_upper)
        
        return None


def get_alternative_message(watched: str, group_name: str, alternative: str) -> str:
    """Generate a user-friendly alternative destination message."""
    return f"You want {watched}? {alternative} is in the same region ({group_name})"
