from typing import Optional
from dataclasses import dataclass


@dataclass
class Airport:
    code: str
    name: str
    city: str
    country: str
    region: str


AIRPORTS: dict[str, Airport] = {
    # New Zealand
    "AKL": Airport("AKL", "Auckland International", "Auckland", "New Zealand", "Oceania"),
    "WLG": Airport("WLG", "Wellington International", "Wellington", "New Zealand", "Oceania"),
    "CHC": Airport("CHC", "Christchurch International", "Christchurch", "New Zealand", "Oceania"),
    "ZQN": Airport("ZQN", "Queenstown", "Queenstown", "New Zealand", "Oceania"),
    "DUD": Airport("DUD", "Dunedin International", "Dunedin", "New Zealand", "Oceania"),
    "NPE": Airport("NPE", "Napier", "Napier", "New Zealand", "Oceania"),
    "NSN": Airport("NSN", "Nelson", "Nelson", "New Zealand", "Oceania"),
    "PMR": Airport("PMR", "Palmerston North", "Palmerston North", "New Zealand", "Oceania"),
    "ROT": Airport("ROT", "Rotorua", "Rotorua", "New Zealand", "Oceania"),
    
    # Australia
    "SYD": Airport("SYD", "Sydney Kingsford Smith", "Sydney", "Australia", "Oceania"),
    "MEL": Airport("MEL", "Melbourne Tullamarine", "Melbourne", "Australia", "Oceania"),
    "BNE": Airport("BNE", "Brisbane International", "Brisbane", "Australia", "Oceania"),
    "PER": Airport("PER", "Perth International", "Perth", "Australia", "Oceania"),
    "ADL": Airport("ADL", "Adelaide International", "Adelaide", "Australia", "Oceania"),
    "CBR": Airport("CBR", "Canberra", "Canberra", "Australia", "Oceania"),
    "OOL": Airport("OOL", "Gold Coast", "Gold Coast", "Australia", "Oceania"),
    "CNS": Airport("CNS", "Cairns International", "Cairns", "Australia", "Oceania"),
    "HBA": Airport("HBA", "Hobart International", "Hobart", "Australia", "Oceania"),
    "DRW": Airport("DRW", "Darwin International", "Darwin", "Australia", "Oceania"),
    
    # Pacific Islands
    "NAN": Airport("NAN", "Nadi International", "Nadi", "Fiji", "Pacific"),
    "SUV": Airport("SUV", "Suva Nausori", "Suva", "Fiji", "Pacific"),
    "RAR": Airport("RAR", "Rarotonga International", "Rarotonga", "Cook Islands", "Pacific"),
    "APW": Airport("APW", "Faleolo International", "Apia", "Samoa", "Pacific"),
    "PPT": Airport("PPT", "Faaa International", "Papeete", "Tahiti", "Pacific"),
    "TBU": Airport("TBU", "Fua'amotu International", "Nuku'alofa", "Tonga", "Pacific"),
    "VLI": Airport("VLI", "Bauerfield International", "Port Vila", "Vanuatu", "Pacific"),
    "NOU": Airport("NOU", "La Tontouta", "Noumea", "New Caledonia", "Pacific"),
    "IUE": Airport("IUE", "Hanan International", "Alofi", "Niue", "Pacific"),
    
    # Hawaii
    "HNL": Airport("HNL", "Daniel K. Inouye International", "Honolulu", "USA", "Hawaii"),
    "OGG": Airport("OGG", "Kahului", "Maui", "USA", "Hawaii"),
    "LIH": Airport("LIH", "Lihue", "Kauai", "USA", "Hawaii"),
    "KOA": Airport("KOA", "Ellison Onizuka Kona", "Kona", "USA", "Hawaii"),
    
    # Japan
    "NRT": Airport("NRT", "Narita International", "Tokyo", "Japan", "Asia"),
    "HND": Airport("HND", "Haneda", "Tokyo", "Japan", "Asia"),
    "KIX": Airport("KIX", "Kansai International", "Osaka", "Japan", "Asia"),
    "NGO": Airport("NGO", "Chubu Centrair", "Nagoya", "Japan", "Asia"),
    "FUK": Airport("FUK", "Fukuoka", "Fukuoka", "Japan", "Asia"),
    "CTS": Airport("CTS", "New Chitose", "Sapporo", "Japan", "Asia"),
    "OKA": Airport("OKA", "Naha", "Okinawa", "Japan", "Asia"),
    
    # Southeast Asia
    "SIN": Airport("SIN", "Changi", "Singapore", "Singapore", "Asia"),
    "BKK": Airport("BKK", "Suvarnabhumi", "Bangkok", "Thailand", "Asia"),
    "HKT": Airport("HKT", "Phuket International", "Phuket", "Thailand", "Asia"),
    "KUL": Airport("KUL", "Kuala Lumpur International", "Kuala Lumpur", "Malaysia", "Asia"),
    "SGN": Airport("SGN", "Tan Son Nhat", "Ho Chi Minh City", "Vietnam", "Asia"),
    "HAN": Airport("HAN", "Noi Bai", "Hanoi", "Vietnam", "Asia"),
    "DAD": Airport("DAD", "Da Nang International", "Da Nang", "Vietnam", "Asia"),
    "DPS": Airport("DPS", "Ngurah Rai", "Bali", "Indonesia", "Asia"),
    "CGK": Airport("CGK", "Soekarno-Hatta", "Jakarta", "Indonesia", "Asia"),
    "MNL": Airport("MNL", "Ninoy Aquino", "Manila", "Philippines", "Asia"),
    "CEB": Airport("CEB", "Mactan-Cebu", "Cebu", "Philippines", "Asia"),
    
    # East Asia
    "HKG": Airport("HKG", "Hong Kong International", "Hong Kong", "Hong Kong", "Asia"),
    "TPE": Airport("TPE", "Taiwan Taoyuan", "Taipei", "Taiwan", "Asia"),
    "ICN": Airport("ICN", "Incheon International", "Seoul", "South Korea", "Asia"),
    "GMP": Airport("GMP", "Gimpo International", "Seoul", "South Korea", "Asia"),
    "PUS": Airport("PUS", "Gimhae International", "Busan", "South Korea", "Asia"),
    "PVG": Airport("PVG", "Pudong International", "Shanghai", "China", "Asia"),
    "SHA": Airport("SHA", "Hongqiao International", "Shanghai", "China", "Asia"),
    "PEK": Airport("PEK", "Beijing Capital", "Beijing", "China", "Asia"),
    "CAN": Airport("CAN", "Baiyun International", "Guangzhou", "China", "Asia"),
    
    # USA West Coast
    "LAX": Airport("LAX", "Los Angeles International", "Los Angeles", "USA", "North America"),
    "SFO": Airport("SFO", "San Francisco International", "San Francisco", "USA", "North America"),
    "SEA": Airport("SEA", "Seattle-Tacoma", "Seattle", "USA", "North America"),
    "PDX": Airport("PDX", "Portland International", "Portland", "USA", "North America"),
    "SAN": Airport("SAN", "San Diego International", "San Diego", "USA", "North America"),
    "LAS": Airport("LAS", "Harry Reid International", "Las Vegas", "USA", "North America"),
    "PHX": Airport("PHX", "Phoenix Sky Harbor", "Phoenix", "USA", "North America"),
    "DEN": Airport("DEN", "Denver International", "Denver", "USA", "North America"),
    
    # USA East Coast
    "JFK": Airport("JFK", "John F Kennedy International", "New York", "USA", "North America"),
    "EWR": Airport("EWR", "Newark Liberty", "New York", "USA", "North America"),
    "LGA": Airport("LGA", "LaGuardia", "New York", "USA", "North America"),
    "BOS": Airport("BOS", "Logan International", "Boston", "USA", "North America"),
    "DCA": Airport("DCA", "Reagan National", "Washington DC", "USA", "North America"),
    "IAD": Airport("IAD", "Dulles International", "Washington DC", "USA", "North America"),
    "MIA": Airport("MIA", "Miami International", "Miami", "USA", "North America"),
    "FLL": Airport("FLL", "Fort Lauderdale-Hollywood", "Fort Lauderdale", "USA", "North America"),
    "ORD": Airport("ORD", "O'Hare International", "Chicago", "USA", "North America"),
    "ATL": Airport("ATL", "Hartsfield-Jackson", "Atlanta", "USA", "North America"),
    "DFW": Airport("DFW", "Dallas/Fort Worth", "Dallas", "USA", "North America"),
    
    # Canada
    "YVR": Airport("YVR", "Vancouver International", "Vancouver", "Canada", "North America"),
    "YYZ": Airport("YYZ", "Toronto Pearson", "Toronto", "Canada", "North America"),
    "YUL": Airport("YUL", "Montreal-Trudeau", "Montreal", "Canada", "North America"),
    "YYC": Airport("YYC", "Calgary International", "Calgary", "Canada", "North America"),
    
    # Europe - UK
    "LHR": Airport("LHR", "Heathrow", "London", "UK", "Europe"),
    "LGW": Airport("LGW", "Gatwick", "London", "UK", "Europe"),
    "STN": Airport("STN", "Stansted", "London", "UK", "Europe"),
    "MAN": Airport("MAN", "Manchester", "Manchester", "UK", "Europe"),
    "EDI": Airport("EDI", "Edinburgh", "Edinburgh", "UK", "Europe"),
    
    # Europe - Western
    "CDG": Airport("CDG", "Charles de Gaulle", "Paris", "France", "Europe"),
    "ORY": Airport("ORY", "Orly", "Paris", "France", "Europe"),
    "AMS": Airport("AMS", "Schiphol", "Amsterdam", "Netherlands", "Europe"),
    "FRA": Airport("FRA", "Frankfurt", "Frankfurt", "Germany", "Europe"),
    "MUC": Airport("MUC", "Munich", "Munich", "Germany", "Europe"),
    "ZRH": Airport("ZRH", "Zurich", "Zurich", "Switzerland", "Europe"),
    "BRU": Airport("BRU", "Brussels", "Brussels", "Belgium", "Europe"),
    "VIE": Airport("VIE", "Vienna International", "Vienna", "Austria", "Europe"),
    "DUB": Airport("DUB", "Dublin", "Dublin", "Ireland", "Europe"),
    
    # Europe - Southern
    "FCO": Airport("FCO", "Fiumicino", "Rome", "Italy", "Europe"),
    "MXP": Airport("MXP", "Malpensa", "Milan", "Italy", "Europe"),
    "BCN": Airport("BCN", "Barcelona-El Prat", "Barcelona", "Spain", "Europe"),
    "MAD": Airport("MAD", "Barajas", "Madrid", "Spain", "Europe"),
    "LIS": Airport("LIS", "Humberto Delgado", "Lisbon", "Portugal", "Europe"),
    "ATH": Airport("ATH", "Eleftherios Venizelos", "Athens", "Greece", "Europe"),
    
    # Europe - Nordic
    "CPH": Airport("CPH", "Copenhagen", "Copenhagen", "Denmark", "Europe"),
    "ARN": Airport("ARN", "Stockholm Arlanda", "Stockholm", "Sweden", "Europe"),
    "OSL": Airport("OSL", "Oslo Gardermoen", "Oslo", "Norway", "Europe"),
    "HEL": Airport("HEL", "Helsinki-Vantaa", "Helsinki", "Finland", "Europe"),
    "KEF": Airport("KEF", "Keflavik", "Reykjavik", "Iceland", "Europe"),
    
    # Middle East
    "DXB": Airport("DXB", "Dubai International", "Dubai", "UAE", "Middle East"),
    "AUH": Airport("AUH", "Abu Dhabi International", "Abu Dhabi", "UAE", "Middle East"),
    "DOH": Airport("DOH", "Hamad International", "Doha", "Qatar", "Middle East"),
    "TLV": Airport("TLV", "Ben Gurion", "Tel Aviv", "Israel", "Middle East"),
    "IST": Airport("IST", "Istanbul", "Istanbul", "Turkey", "Middle East"),
    
    # South America
    "GRU": Airport("GRU", "Guarulhos", "Sao Paulo", "Brazil", "South America"),
    "GIG": Airport("GIG", "Galeao", "Rio de Janeiro", "Brazil", "South America"),
    "EZE": Airport("EZE", "Ministro Pistarini", "Buenos Aires", "Argentina", "South America"),
    "SCL": Airport("SCL", "Arturo Merino Benitez", "Santiago", "Chile", "South America"),
    "LIM": Airport("LIM", "Jorge Chavez", "Lima", "Peru", "South America"),
    "BOG": Airport("BOG", "El Dorado", "Bogota", "Colombia", "South America"),
    
    # South Asia
    "DEL": Airport("DEL", "Indira Gandhi International", "Delhi", "India", "Asia"),
    "BOM": Airport("BOM", "Chhatrapati Shivaji", "Mumbai", "India", "Asia"),
    "CMB": Airport("CMB", "Bandaranaike", "Colombo", "Sri Lanka", "Asia"),
    "MLE": Airport("MLE", "Velana International", "Male", "Maldives", "Asia"),
    
    # Africa
    "JNB": Airport("JNB", "O.R. Tambo", "Johannesburg", "South Africa", "Africa"),
    "CPT": Airport("CPT", "Cape Town International", "Cape Town", "South Africa", "Africa"),
    "CAI": Airport("CAI", "Cairo International", "Cairo", "Egypt", "Africa"),
    "NBO": Airport("NBO", "Jomo Kenyatta", "Nairobi", "Kenya", "Africa"),
    "MRU": Airport("MRU", "Sir Seewoosagur Ramgoolam", "Mauritius", "Mauritius", "Africa"),
}


class AirportService:
    
    @staticmethod
    def is_valid(code: str) -> bool:
        """Check if an airport code is valid (exists in our database)."""
        if not code or len(code) != 3:
            return False
        return code.upper() in AIRPORTS
    
    @staticmethod
    def validate(code: str) -> tuple[bool, Optional[str]]:
        """
        Validate an airport code and return (is_valid, error_message).
        
        Returns:
            (True, None) if valid
            (False, "error message") if invalid
        """
        if not code:
            return False, "Airport code is required"
        
        code = code.strip().upper()
        
        if len(code) != 3:
            return False, f"Airport code must be 3 characters, got '{code}'"
        
        if not code.isalpha():
            return False, f"Airport code must contain only letters, got '{code}'"
        
        if code in AIRPORTS:
            return True, None
        
        # Code is well-formed but not in our database - suggest alternatives
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
