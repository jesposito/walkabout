import json
import logging
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    NONE = "none"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass
class ParsedDealResult:
    origin: Optional[str] = None
    destination: Optional[str] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    cabin_class: Optional[str] = None
    confidence: float = 0.0
    raw_response: Optional[str] = None


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
    async def complete(self, prompt: str) -> str:
        pass


class OpenAIBackend(AIBackend):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
    
    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 200,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AnthropicBackend(AIBackend):
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key
        self.model = model
    
    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]


class GeminiBackend(AIBackend):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
    
    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                params={"key": self.api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0, "maxOutputTokens": 200},
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]


class OllamaBackend(AIBackend):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0},
                },
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
    
    async def complete(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 200,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


class AIService:
    _instance: Optional["AIService"] = None
    _backend: Optional[AIBackend] = None
    _provider: AIProvider = AIProvider.NONE
    
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
            cls._backend = OpenAIBackend(api_key, model or "gpt-4o-mini")
        elif provider == AIProvider.ANTHROPIC and api_key:
            cls._backend = AnthropicBackend(api_key, model or "claude-3-haiku-20240307")
        elif provider == AIProvider.GEMINI and api_key:
            cls._backend = GeminiBackend(api_key, model or "gemini-1.5-flash")
        elif provider == AIProvider.OLLAMA:
            cls._backend = OllamaBackend(base_url or "http://localhost:11434", model or "llama3.2")
        elif provider == AIProvider.OPENAI_COMPATIBLE and api_key and base_url and model:
            cls._backend = OpenAICompatibleBackend(base_url, api_key, model)
        else:
            cls._backend = None
    
    @classmethod
    def is_configured(cls) -> bool:
        return cls._backend is not None
    
    @classmethod
    def get_provider(cls) -> AIProvider:
        return cls._provider
    
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
