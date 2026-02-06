import json
import hashlib
import logging
import time
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    NONE = "none"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


# Cost rates per 1K tokens (USD)
COST_RATES: Dict[str, Dict[str, float]] = {
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-haiku-latest": {"input": 0.00025, "output": 0.00125},
    "claude-3-5-sonnet-latest": {"input": 0.003, "output": 0.015},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
}

# Default rates by provider (for unknown models)
PROVIDER_DEFAULT_RATES: Dict[str, Dict[str, float]] = {
    "anthropic": {"input": 0.00025, "output": 0.00125},
    "openai": {"input": 0.00015, "output": 0.0006},
    "gemini": {"input": 0.00015, "output": 0.0006},
    "ollama": {"input": 0.0, "output": 0.0},
    "openai_compatible": {"input": 0.00015, "output": 0.0006},
    "none": {"input": 0.0, "output": 0.0},
}


@dataclass
class ParsedDealResult:
    origin: Optional[str] = None
    destination: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    cabin_class: Optional[str] = None
    confidence: float = 0.0
    raw_response: Optional[str] = None


@dataclass
class CacheEntry:
    response: str
    timestamp: float


DEAL_PARSE_PROMPT = """Extract flight deal information from this title. Return JSON only.

Title: {title}

Extract:
- origin: 3-letter IATA airport code for departure city (e.g., MEL, SYD, AKL)
- destination: 3-letter IATA airport code for arrival city (e.g., NRT, HKG, LAX)
- price: lowest price mentioned as integer (no currency symbol)
- currency: 3-letter currency code (usually USD, AUD, or NZD)
- cabin_class: "economy", "premium_economy", "business", or "first"

Rules:
- "X from Y" means Y is origin, X is destination
- "X to Y" means X is origin, Y is destination
- If multiple routes listed, extract the FIRST route only
- Use major airport codes: Sydney=SYD, Melbourne=MEL, Perth=PER, Auckland=AKL, Tokyo=NRT, Hong Kong=HKG
- Default cabin_class to "economy" unless business/first mentioned

Return ONLY valid JSON, no explanation:
{{"origin": "XXX", "destination": "YYY", "price": 123, "currency": "USD", "cabin_class": "economy"}}"""


class AIBackend(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 500) -> str:
        pass


class OpenAIBackend(AIBackend):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    async def complete(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 500) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AnthropicBackend(AIBackend):
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key
        self.model = model

    async def complete(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 500) -> str:
        request_json: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            request_json["system"] = system_prompt

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=request_json,
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]


class GeminiBackend(AIBackend):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model

    async def complete(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 500) -> str:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                params={"key": self.api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]


class OllamaBackend(AIBackend):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 500) -> str:
        request_json: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
        }
        if system_prompt:
            request_json["system"] = system_prompt

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=request_json,
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]


class OpenAICompatibleBackend(AIBackend):
    """Generic backend for any OpenAI-compatible API (Groq, Together, OpenRouter, Azure, etc.)"""
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def complete(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 500) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AIService:
    _instance: Optional["AIService"] = None
    _backend: Optional[AIBackend] = None
    _provider: AIProvider = AIProvider.NONE
    _model: Optional[str] = None
    _cache: Dict[str, CacheEntry] = {}
    _cache_ttl: float = 3600.0  # 1 hour default

    @classmethod
    def configure(
        cls,
        provider: AIProvider,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        cls._provider = provider

        if provider == AIProvider.OPENAI and api_key:
            cls._model = model or "gpt-4o-mini"
            cls._backend = OpenAIBackend(api_key, cls._model)
        elif provider == AIProvider.ANTHROPIC and api_key:
            cls._model = model or "claude-3-haiku-20240307"
            cls._backend = AnthropicBackend(api_key, cls._model)
        elif provider == AIProvider.GEMINI and api_key:
            cls._model = model or "gemini-1.5-flash"
            cls._backend = GeminiBackend(api_key, cls._model)
        elif provider == AIProvider.OLLAMA:
            cls._model = model or "llama3.2"
            cls._backend = OllamaBackend(base_url or "http://localhost:11434", cls._model)
        elif provider == AIProvider.OPENAI_COMPATIBLE and api_key and base_url and model:
            cls._model = model
            cls._backend = OpenAICompatibleBackend(base_url, api_key, model)
        else:
            cls._backend = None
            cls._model = None

    @classmethod
    def is_configured(cls) -> bool:
        return cls._backend is not None

    @classmethod
    def get_provider(cls) -> AIProvider:
        return cls._provider

    @classmethod
    def get_model(cls) -> Optional[str]:
        return cls._model

    @staticmethod
    def _make_cache_key(prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a hash key for caching based on prompt content."""
        combined = (system_prompt or "") + "||" + prompt
        return hashlib.sha256(combined.encode()).hexdigest()

    @classmethod
    def _get_cached(cls, cache_key: str) -> Optional[str]:
        """Return cached response if it exists and hasn't expired."""
        entry = cls._cache.get(cache_key)
        if entry is None:
            return None
        if (time.time() - entry.timestamp) > cls._cache_ttl:
            del cls._cache[cache_key]
            return None
        return entry.response

    @classmethod
    def _set_cached(cls, cache_key: str, response: str) -> None:
        """Store a response in the cache."""
        cls._cache[cache_key] = CacheEntry(response=response, timestamp=time.time())

    @classmethod
    def clear_cache(cls) -> int:
        """Clear all cached responses. Returns the number of entries cleared."""
        count = len(cls._cache)
        cls._cache.clear()
        return count

    @classmethod
    def set_cache_ttl(cls, ttl_seconds: float) -> None:
        """Set the cache TTL in seconds."""
        cls._cache_ttl = ttl_seconds

    @classmethod
    def _get_cost_rates(cls) -> Dict[str, float]:
        """Get cost rates for the current model/provider."""
        if cls._model and cls._model in COST_RATES:
            return COST_RATES[cls._model]
        provider_key = cls._provider.value
        return PROVIDER_DEFAULT_RATES.get(provider_key, {"input": 0.0, "output": 0.0})

    @classmethod
    def estimate_tokens(
        cls,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """Estimate token counts and cost for a prompt without executing it.

        Uses a rough word-count heuristic: words * 1.3 for input tokens.
        Output tokens are estimated as max_tokens.
        """
        input_text = prompt
        if system_prompt:
            input_text = system_prompt + " " + prompt

        word_count = len(input_text.split())
        input_tokens_est = int(word_count * 1.3)
        output_tokens_est = max_tokens

        rates = cls._get_cost_rates()
        cost_est_usd = (
            (input_tokens_est / 1000.0) * rates["input"]
            + (output_tokens_est / 1000.0) * rates["output"]
        )

        return {
            "input_tokens_est": input_tokens_est,
            "output_tokens_est": output_tokens_est,
            "cost_est_usd": round(cost_est_usd, 8),
        }

    @classmethod
    def _log_usage(
        cls,
        db,
        endpoint: str,
        prompt_hash: str,
        input_tokens_est: int,
        output_tokens_est: int,
        cost_est_usd: float,
        cached: bool,
    ) -> None:
        """Log AI usage to the database if a db session is provided."""
        if db is None:
            return
        try:
            from app.models.ai_usage import AIUsageLog

            log_entry = AIUsageLog(
                endpoint=endpoint,
                provider=cls._provider.value,
                model=cls._model or "unknown",
                input_tokens_est=input_tokens_est,
                output_tokens_est=output_tokens_est,
                cost_est_usd=cost_est_usd,
                cached=cached,
                prompt_hash=prompt_hash,
            )
            db.add(log_entry)
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to log AI usage: {e}")

    @classmethod
    async def complete(
        cls,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        db=None,
        endpoint: str = "general",
    ) -> str:
        """General-purpose completion method that works across all configured providers.

        Args:
            prompt: The user prompt to complete.
            system_prompt: Optional system prompt for context.
            max_tokens: Maximum tokens in the response.
            db: Optional database session for usage logging.
            endpoint: String identifying which feature triggered this call.

        Returns:
            The completion response text.

        Raises:
            RuntimeError: If no AI backend is configured.
        """
        if not cls._backend:
            raise RuntimeError("AI service is not configured. Set up a provider first.")

        cache_key = cls._make_cache_key(prompt, system_prompt)
        estimate = cls.estimate_tokens(prompt, system_prompt, max_tokens)

        # Check cache
        cached_response = cls._get_cached(cache_key)
        if cached_response is not None:
            logger.debug(f"AI cache hit for endpoint={endpoint}")
            cls._log_usage(
                db=db,
                endpoint=endpoint,
                prompt_hash=cache_key,
                input_tokens_est=estimate["input_tokens_est"],
                output_tokens_est=estimate["output_tokens_est"],
                cost_est_usd=0.0,  # no cost for cached responses
                cached=True,
            )
            return cached_response

        # Call the backend
        response = await cls._backend.complete(prompt, system_prompt, max_tokens)

        # Cache the response
        cls._set_cached(cache_key, response)

        # Log usage
        cls._log_usage(
            db=db,
            endpoint=endpoint,
            prompt_hash=cache_key,
            input_tokens_est=estimate["input_tokens_est"],
            output_tokens_est=estimate["output_tokens_est"],
            cost_est_usd=estimate["cost_est_usd"],
            cached=False,
        )

        return response

    @classmethod
    async def parse_deal(cls, title: str) -> ParsedDealResult:
        if not cls._backend:
            return ParsedDealResult(confidence=0.0)

        prompt = DEAL_PARSE_PROMPT.format(title=title)

        try:
            response = await cls._backend.complete(prompt)
            cls._last_response = response

            json_str = response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            json_str = json_str.strip()

            data = json.loads(json_str)

            origin = data.get("origin", "").upper() if data.get("origin") else None
            destination = data.get("destination", "").upper() if data.get("destination") else None

            if origin and len(origin) != 3:
                origin = None
            if destination and len(destination) != 3:
                destination = None

            confidence = 0.9 if (origin and destination) else 0.5

            return ParsedDealResult(
                origin=origin,
                destination=destination,
                price=int(data["price"]) if data.get("price") else None,
                currency=data.get("currency", "USD").upper(),
                cabin_class=data.get("cabin_class", "economy"),
                confidence=confidence,
                raw_response=response,
            )
        except Exception as e:
            logger.warning(f"AI parse failed for '{title[:50]}...': {e}")
            return ParsedDealResult(confidence=0.0, raw_response=str(e))


def configure_ai_from_settings(settings) -> bool:
    provider = AIProvider(settings.ai_provider or "none")

    if provider == AIProvider.NONE:
        AIService.configure(AIProvider.NONE)
        return False

    AIService.configure(
        provider=provider,
        api_key=settings.ai_api_key,
        base_url=settings.ai_ollama_url,
        model=settings.ai_model,
    )

    return AIService.is_configured()
