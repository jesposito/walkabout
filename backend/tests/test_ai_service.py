"""Tests for AIService enhancements: token estimation, caching, cost estimation, and complete()."""
import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ai_service import (
    AIService,
    AIProvider,
    AIBackend,
    CacheEntry,
    COST_RATES,
    PROVIDER_DEFAULT_RATES,
)


class MockBackend(AIBackend):
    """A mock backend that returns a fixed response."""

    def __init__(self, response: str = "mock response"):
        self.response = response
        self.call_count = 0
        self.last_prompt = None
        self.last_system_prompt = None
        self.last_max_tokens = None

    async def complete(self, prompt, system_prompt=None, max_tokens=500):
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt
        self.last_max_tokens = max_tokens
        return self.response


@pytest.fixture(autouse=True)
def reset_ai_service():
    """Reset AIService state before each test."""
    AIService._backend = None
    AIService._provider = AIProvider.NONE
    AIService._model = None
    AIService._cache = {}
    AIService._cache_ttl = 3600.0
    yield
    AIService._backend = None
    AIService._provider = AIProvider.NONE
    AIService._model = None
    AIService._cache = {}
    AIService._cache_ttl = 3600.0


def _configure_mock(response="mock response"):
    """Helper to configure AIService with a mock backend."""
    backend = MockBackend(response=response)
    AIService._backend = backend
    AIService._provider = AIProvider.ANTHROPIC
    AIService._model = "claude-3-haiku-20240307"
    return backend


class TestEstimateTokens:
    def test_basic_word_count_heuristic(self):
        """Token estimation uses words * 1.3."""
        prompt = "hello world"
        result = AIService.estimate_tokens(prompt)
        # 2 words * 1.3 = 2.6 -> int(2.6) = 2
        assert result["input_tokens_est"] == 2

    def test_includes_system_prompt_in_word_count(self):
        """System prompt words are included in input token estimate."""
        prompt = "hello"
        system_prompt = "you are helpful"
        result = AIService.estimate_tokens(prompt, system_prompt)
        # "you are helpful hello" = 4 words * 1.3 = 5.2 -> int(5.2) = 5
        assert result["input_tokens_est"] == 5

    def test_output_tokens_equals_max_tokens(self):
        """Output token estimate is max_tokens."""
        result = AIService.estimate_tokens("hello", max_tokens=200)
        assert result["output_tokens_est"] == 200

    def test_default_max_tokens(self):
        """Default max_tokens is 500."""
        result = AIService.estimate_tokens("hello")
        assert result["output_tokens_est"] == 500

    def test_cost_estimation_with_known_model(self):
        """Cost is calculated using model-specific rates."""
        _configure_mock()
        prompt = "word " * 100  # 100 words
        result = AIService.estimate_tokens(prompt, max_tokens=200)
        input_tokens = int(100 * 1.3)  # 130
        output_tokens = 200
        # claude-3-haiku rates: input $0.00025/1K, output $0.00125/1K
        expected_cost = (130 / 1000) * 0.00025 + (200 / 1000) * 0.00125
        assert result["cost_est_usd"] == pytest.approx(expected_cost, abs=1e-7)

    def test_cost_estimation_with_unknown_model_uses_provider_default(self):
        """Unknown model falls back to provider default rates."""
        AIService._provider = AIProvider.OPENAI
        AIService._model = "custom-model-xyz"
        AIService._backend = MockBackend()
        prompt = "word " * 100
        result = AIService.estimate_tokens(prompt, max_tokens=100)
        input_tokens = int(100 * 1.3)
        # openai default rates: input $0.00015/1K, output $0.0006/1K
        expected_cost = (input_tokens / 1000) * 0.00015 + (100 / 1000) * 0.0006
        assert result["cost_est_usd"] == pytest.approx(expected_cost, abs=1e-7)

    def test_ollama_zero_cost(self):
        """Ollama provider has zero cost."""
        AIService._provider = AIProvider.OLLAMA
        AIService._model = "llama3.2"
        AIService._backend = MockBackend()
        result = AIService.estimate_tokens("some prompt", max_tokens=500)
        assert result["cost_est_usd"] == 0.0

    def test_empty_prompt(self):
        """Empty prompt results in 0 input tokens."""
        result = AIService.estimate_tokens("")
        # "".split() returns [] which has length 0 -> 0 * 1.3 = 0
        assert result["input_tokens_est"] == 0

    def test_long_prompt(self):
        """Long prompts produce proportional token estimates."""
        prompt = "word " * 1000
        result = AIService.estimate_tokens(prompt)
        assert result["input_tokens_est"] == int(1000 * 1.3)


class TestCacheBehavior:
    def test_cache_key_consistency(self):
        """Same inputs produce same cache key."""
        key1 = AIService._make_cache_key("hello", "system")
        key2 = AIService._make_cache_key("hello", "system")
        assert key1 == key2

    def test_cache_key_differs_for_different_prompts(self):
        """Different prompts produce different cache keys."""
        key1 = AIService._make_cache_key("hello")
        key2 = AIService._make_cache_key("world")
        assert key1 != key2

    def test_cache_key_includes_system_prompt(self):
        """System prompt affects cache key."""
        key1 = AIService._make_cache_key("hello", "system1")
        key2 = AIService._make_cache_key("hello", "system2")
        assert key1 != key2

    def test_cache_key_none_vs_no_system_prompt(self):
        """None system prompt produces consistent key."""
        key1 = AIService._make_cache_key("hello", None)
        key2 = AIService._make_cache_key("hello")
        assert key1 == key2

    def test_set_and_get_cached(self):
        """Cached entries can be stored and retrieved."""
        AIService._set_cached("key1", "response1")
        assert AIService._get_cached("key1") == "response1"

    def test_cache_miss_returns_none(self):
        """Missing cache entries return None."""
        assert AIService._get_cached("nonexistent") is None

    def test_cache_expiry(self):
        """Expired cache entries are removed and return None."""
        AIService._cache_ttl = 0.1  # 100ms TTL
        AIService._set_cached("key1", "response1")
        time.sleep(0.2)
        assert AIService._get_cached("key1") is None

    def test_clear_cache(self):
        """clear_cache removes all entries and returns count."""
        AIService._set_cached("key1", "r1")
        AIService._set_cached("key2", "r2")
        count = AIService.clear_cache()
        assert count == 2
        assert AIService._get_cached("key1") is None
        assert AIService._get_cached("key2") is None

    def test_set_cache_ttl(self):
        """set_cache_ttl changes the TTL."""
        AIService.set_cache_ttl(7200.0)
        assert AIService._cache_ttl == 7200.0


class TestCostEstimation:
    def test_known_model_rates_gpt4o_mini(self):
        """GPT-4o-mini has correct rates."""
        AIService._provider = AIProvider.OPENAI
        AIService._model = "gpt-4o-mini"
        AIService._backend = MockBackend()
        rates = AIService._get_cost_rates()
        assert rates == {"input": 0.00015, "output": 0.0006}

    def test_known_model_rates_claude_haiku(self):
        """Claude Haiku has correct rates."""
        AIService._provider = AIProvider.ANTHROPIC
        AIService._model = "claude-3-haiku-20240307"
        AIService._backend = MockBackend()
        rates = AIService._get_cost_rates()
        assert rates == {"input": 0.00025, "output": 0.00125}

    def test_known_model_rates_gpt4o(self):
        """GPT-4o has correct rates."""
        AIService._provider = AIProvider.OPENAI
        AIService._model = "gpt-4o"
        AIService._backend = MockBackend()
        rates = AIService._get_cost_rates()
        assert rates == {"input": 0.0025, "output": 0.01}

    def test_unknown_model_uses_provider_defaults(self):
        """Unknown model falls back to provider defaults."""
        AIService._provider = AIProvider.GEMINI
        AIService._model = "gemini-pro-whatever"
        AIService._backend = MockBackend()
        rates = AIService._get_cost_rates()
        assert rates == PROVIDER_DEFAULT_RATES["gemini"]

    def test_unconfigured_provider_zero_cost(self):
        """Unconfigured provider defaults to zero cost."""
        rates = AIService._get_cost_rates()
        assert rates == {"input": 0.0, "output": 0.0}


class TestComplete:
    def test_complete_raises_when_not_configured(self):
        """complete() raises RuntimeError when no backend is configured."""
        with pytest.raises(RuntimeError, match="not configured"):
            asyncio.get_event_loop().run_until_complete(
                AIService.complete("hello")
            )

    def test_complete_returns_response(self):
        """complete() returns the backend response."""
        backend = _configure_mock("test response")
        result = asyncio.get_event_loop().run_until_complete(
            AIService.complete("hello world")
        )
        assert result == "test response"
        assert backend.call_count == 1

    def test_complete_passes_system_prompt(self):
        """complete() passes system_prompt to the backend."""
        backend = _configure_mock()
        asyncio.get_event_loop().run_until_complete(
            AIService.complete("hello", system_prompt="be helpful")
        )
        assert backend.last_system_prompt == "be helpful"

    def test_complete_passes_max_tokens(self):
        """complete() passes max_tokens to the backend."""
        backend = _configure_mock()
        asyncio.get_event_loop().run_until_complete(
            AIService.complete("hello", max_tokens=100)
        )
        assert backend.last_max_tokens == 100

    def test_complete_caches_response(self):
        """Second identical call returns cached response without calling backend."""
        backend = _configure_mock("cached result")
        loop = asyncio.get_event_loop()

        result1 = loop.run_until_complete(AIService.complete("same prompt"))
        result2 = loop.run_until_complete(AIService.complete("same prompt"))

        assert result1 == "cached result"
        assert result2 == "cached result"
        assert backend.call_count == 1  # Only called once

    def test_complete_different_prompts_not_cached(self):
        """Different prompts are not cached together."""
        backend = _configure_mock("response")
        loop = asyncio.get_event_loop()

        loop.run_until_complete(AIService.complete("prompt one"))
        loop.run_until_complete(AIService.complete("prompt two"))

        assert backend.call_count == 2

    def test_complete_logs_usage_to_db(self):
        """complete() logs usage when db is provided."""
        _configure_mock("response")
        mock_db = MagicMock()
        loop = asyncio.get_event_loop()

        loop.run_until_complete(
            AIService.complete("hello", db=mock_db, endpoint="test_endpoint")
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        logged_entry = mock_db.add.call_args[0][0]
        assert logged_entry.endpoint == "test_endpoint"
        assert logged_entry.provider == "anthropic"
        assert logged_entry.model == "claude-3-haiku-20240307"
        assert logged_entry.cached is False

    def test_complete_cached_logs_zero_cost(self):
        """Cached responses log zero cost."""
        _configure_mock("response")
        mock_db = MagicMock()
        loop = asyncio.get_event_loop()

        # First call (not cached)
        loop.run_until_complete(AIService.complete("hello", db=mock_db))
        # Second call (cached)
        loop.run_until_complete(AIService.complete("hello", db=mock_db))

        # Second log entry should have cached=True and zero cost
        second_entry = mock_db.add.call_args_list[1][0][0]
        assert second_entry.cached is True
        assert second_entry.cost_est_usd == 0.0

    def test_complete_no_db_does_not_fail(self):
        """complete() works without a db session."""
        _configure_mock("response")
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(AIService.complete("hello"))
        assert result == "response"


class TestConfigure:
    def test_configure_anthropic(self):
        """Configuring Anthropic sets correct provider and model."""
        AIService.configure(AIProvider.ANTHROPIC, api_key="test-key")
        assert AIService.is_configured()
        assert AIService.get_provider() == AIProvider.ANTHROPIC
        assert AIService.get_model() == "claude-3-haiku-20240307"

    def test_configure_openai(self):
        """Configuring OpenAI sets correct provider and model."""
        AIService.configure(AIProvider.OPENAI, api_key="test-key")
        assert AIService.is_configured()
        assert AIService.get_provider() == AIProvider.OPENAI
        assert AIService.get_model() == "gpt-4o-mini"

    def test_configure_ollama(self):
        """Configuring Ollama sets correct provider and model."""
        AIService.configure(AIProvider.OLLAMA)
        assert AIService.is_configured()
        assert AIService.get_provider() == AIProvider.OLLAMA
        assert AIService.get_model() == "llama3.2"

    def test_configure_custom_model(self):
        """Custom model name is preserved."""
        AIService.configure(AIProvider.OPENAI, api_key="k", model="gpt-4o")
        assert AIService.get_model() == "gpt-4o"

    def test_configure_none(self):
        """Configuring NONE provider leaves service unconfigured."""
        AIService.configure(AIProvider.NONE)
        assert not AIService.is_configured()
        assert AIService.get_model() is None

    def test_configure_without_required_key(self):
        """Configuring without required API key leaves service unconfigured."""
        AIService.configure(AIProvider.OPENAI)  # No api_key
        assert not AIService.is_configured()
