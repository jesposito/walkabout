from dataclasses import dataclass
from typing import Optional
import json
import logging
import hashlib

from app.config import get_settings
from app.models.deal import ParseStatus
from app.services.feeds.base import ParseResult, ParsedDeal

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Extract flight deal information from this text. Return ONLY valid JSON.

Text: {text}

Extract these fields (use "unknown" if not found, never invent data):
- origin: departure city or airport code
- destination: arrival city or airport code  
- price: numeric price (integer, no currency symbol)
- currency: ISO currency code (USD, EUR, GBP, NZD, AUD, etc.)
- cabin_class: one of [economy, premium_economy, business, first, unknown]
- airline: airline name if mentioned, else unknown
- travel_dates: date range if mentioned, else unknown

Return JSON:
{{"origin": "...", "destination": "...", "price": 0, "currency": "...", "cabin_class": "...", "airline": "...", "travel_dates": "...", "confidence": 0.0}}

Set confidence 0.0-1.0 based on how clearly the information was stated."""


INSIGHTS_PROMPT = """Analyze these flight deals for patterns and insights.

Deals (last {days} days):
{deals_summary}

User's home airport: {home_airport}
User's watched destinations: {destinations}

Provide insights in JSON format:
{{
  "price_trends": [
    {{"route": "AKL-SYD", "trend": "decreasing", "note": "..."}}
  ],
  "best_time_to_book": {{"insight": "...", "confidence": 0.0}},
  "unusual_deals": [
    {{"deal": "...", "why_unusual": "..."}}
  ],
  "recommendations": [
    {{"action": "...", "reason": "..."}}
  ],
  "market_observations": "..."
}}"""


@dataclass
class AIConfig:
    enabled: bool = False
    api_key: str = ""
    model: str = "claude-3-haiku-20240307"
    max_monthly_calls: int = 1000
    fallback_threshold: float = 0.4


class AIExtractor:
    
    def __init__(self, config: Optional[AIConfig] = None):
        settings = get_settings()
        self.config = config or AIConfig(
            enabled=bool(settings.anthropic_api_key),
            api_key=settings.anthropic_api_key,
            model="claude-3-haiku-20240307",
        )
        self._call_count = 0
        self._cache: dict[str, ParseResult] = {}
    
    def should_use_ai(self, result: ParseResult) -> bool:
        if not self.config.enabled:
            return False
        if self._call_count >= self.config.max_monthly_calls:
            logger.warning("AI extraction monthly limit reached")
            return False
        return result.confidence < self.config.fallback_threshold
    
    async def extract(self, deal: ParsedDeal) -> ParseResult:
        if not self.config.enabled:
            return deal.result

        cache_key = self._cache_key(deal)
        if cache_key in self._cache:
            logger.debug(f"AI cache hit for {cache_key}")
            return self._cache[cache_key]

        try:
            result = await self._call_api(deal)
            # Validate: if generic parser found valid airports, don't replace
            # with AI airports unless they match city names in the title
            result = self._validate_against_original(deal, result)
            self._cache[cache_key] = result
            self._call_count += 1
            return result
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return deal.result

    def _validate_against_original(self, deal: ParsedDeal, ai_result: ParseResult) -> ParseResult:
        """Prevent AI from replacing valid route data with hallucinated airports."""
        original = deal.result

        # If the generic parser found valid airports, keep them unless AI matches title
        if original.origin and original.destination:
            from app.services.airports import AirportLookup, AIRPORTS, CITY_TO_CODES

            # Verify AI airports actually appear in the title text
            title_lower = deal.raw_title.lower()
            ai_origin_valid = self._airport_matches_text(ai_result.origin, title_lower)
            ai_dest_valid = self._airport_matches_text(ai_result.destination, title_lower)

            if not (ai_origin_valid and ai_dest_valid):
                logger.warning(
                    f"AI hallucinated airports for '{deal.raw_title[:80]}': "
                    f"AI={ai_result.origin}->{ai_result.destination}, "
                    f"keeping generic={original.origin}->{original.destination}"
                )
                ai_result.origin = original.origin
                ai_result.destination = original.destination

        return ai_result

    @staticmethod
    def _airport_matches_text(code: str | None, text_lower: str) -> bool:
        """Check if an airport code or its city name appears in the text."""
        if not code:
            return False
        code = code.upper()
        # Direct code mention
        if code.lower() in text_lower or code in text_lower.upper():
            return True
        # Check if the city name for this code appears in the text
        from app.services.airports import AIRPORTS, CITY_TO_CODES
        airport_info = AIRPORTS.get(code)
        if airport_info:
            city = airport_info.get('city', '').lower()
            if city and city in text_lower:
                return True
        # Check reverse: city_to_codes
        for city, codes in CITY_TO_CODES.items():
            if code in codes and city in text_lower:
                return True
        return False
    
    async def _call_api(self, deal: ParsedDeal) -> ParseResult:
        import httpx
        
        text = f"{deal.raw_title}\n{deal.raw_summary or ''}"
        prompt = EXTRACTION_PROMPT.format(text=text[:1000])
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.config.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "max_tokens": 500,
                    "temperature": 0.1,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            
        data = response.json()
        content = data["content"][0]["text"]
        
        return self._parse_response(content)
    
    def _parse_response(self, content: str) -> ParseResult:
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                parsed = json.loads(json_str)
                
                return ParseResult(
                    origin=parsed.get("origin") if parsed.get("origin") != "unknown" else None,
                    destination=parsed.get("destination") if parsed.get("destination") != "unknown" else None,
                    price=int(parsed["price"]) if parsed.get("price") and parsed["price"] != "unknown" else None,
                    currency=parsed.get("currency") if parsed.get("currency") != "unknown" else None,
                    cabin_class=parsed.get("cabin_class") if parsed.get("cabin_class") != "unknown" else None,
                    airline=parsed.get("airline") if parsed.get("airline") != "unknown" else None,
                    travel_dates=parsed.get("travel_dates") if parsed.get("travel_dates") != "unknown" else None,
                    confidence=float(parsed.get("confidence", 0.7)),
                    status=ParseStatus.SUCCESS,
                    parser_used="ai_claude",
                )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
        
        return ParseResult(
            status=ParseStatus.FAILED,
            reasons=["AI response parsing failed"],
            parser_used="ai_claude",
        )
    
    def _cache_key(self, deal: ParsedDeal) -> str:
        if deal.input_hash:
            return f"{deal.input_hash}:{self.config.model}"
        text = f"{deal.raw_title}:{deal.raw_summary or ''}"
        return hashlib.sha256(text.encode()).hexdigest()[:16]


class AIInsightsEngine:
    
    def __init__(self, config: Optional[AIConfig] = None):
        settings = get_settings()
        self.config = config or AIConfig(
            enabled=bool(settings.anthropic_api_key),
            api_key=settings.anthropic_api_key,
            model="claude-3-5-sonnet-20241022",
        )
    
    async def generate_insights(
        self,
        deals: list[dict],
        home_airport: str,
        watched_destinations: list[str],
        days: int = 30,
    ) -> dict:
        if not self.config.enabled:
            return {"error": "AI insights not enabled", "enabled": False}
        
        deals_summary = self._summarize_deals(deals)
        
        prompt = INSIGHTS_PROMPT.format(
            days=days,
            deals_summary=deals_summary,
            home_airport=home_airport,
            destinations=", ".join(watched_destinations),
        )
        
        try:
            return await self._call_api(prompt)
        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            return {"error": str(e)}
    
    def _summarize_deals(self, deals: list[dict]) -> str:
        lines = []
        for d in deals[:50]:
            line = f"- {d.get('origin', '?')} to {d.get('destination', '?')}: ${d.get('price', '?')} {d.get('currency', '')} ({d.get('cabin_class', 'economy')})"
            if d.get('airline'):
                line += f" on {d['airline']}"
            lines.append(line)
        return "\n".join(lines)
    
    async def _call_api(self, prompt: str) -> dict:
        import httpx
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.config.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.config.model,
                    "max_tokens": 2000,
                    "temperature": 0.3,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            
        data = response.json()
        content = data["content"][0]["text"]
        
        start = content.find('{')
        end = content.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        
        return {"raw_response": content}
