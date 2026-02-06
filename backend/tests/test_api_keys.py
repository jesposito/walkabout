"""
Tests for centralized API key resolution (api_keys.py).
"""
import pytest
from unittest.mock import MagicMock, patch


def _make_settings_obj(**kwargs):
    """Create a mock UserSettings with given attributes."""
    obj = MagicMock()
    for k, v in kwargs.items():
        setattr(obj, k, v)
    return obj


class TestGetApiKey:
    """Test get_api_key resolution order: DB first, then env var."""

    def test_returns_db_value_when_present(self):
        from app.services.api_keys import get_api_key

        mock_db = MagicMock()
        settings_row = _make_settings_obj(serpapi_key="db-key-123")
        mock_db.query.return_value.filter.return_value.first.return_value = settings_row

        result = get_api_key("serpapi_key", mock_db)
        assert result == "db-key-123"

    def test_strips_whitespace_from_db_value(self):
        from app.services.api_keys import get_api_key

        mock_db = MagicMock()
        settings_row = _make_settings_obj(serpapi_key="  spaced-key  ")
        mock_db.query.return_value.filter.return_value.first.return_value = settings_row

        result = get_api_key("serpapi_key", mock_db)
        assert result == "spaced-key"

    def test_skips_empty_db_value_falls_back_to_env(self):
        from app.services.api_keys import get_api_key

        mock_db = MagicMock()
        settings_row = _make_settings_obj(serpapi_key="  ")
        mock_db.query.return_value.filter.return_value.first.return_value = settings_row

        with patch("app.services.api_keys.get_settings") as mock_settings:
            mock_env = MagicMock()
            mock_env.serpapi_key = "env-key-456"
            mock_settings.return_value = mock_env
            result = get_api_key("serpapi_key", mock_db)

        assert result == "env-key-456"

    def test_returns_env_value_when_no_db(self):
        from app.services.api_keys import get_api_key

        with patch("app.services.api_keys.get_settings") as mock_settings:
            mock_env = MagicMock()
            mock_env.serpapi_key = "env-key-789"
            mock_settings.return_value = mock_env
            result = get_api_key("serpapi_key", None)

        assert result == "env-key-789"

    def test_returns_none_when_nothing_configured(self):
        from app.services.api_keys import get_api_key

        with patch("app.services.api_keys.get_settings") as mock_settings:
            mock_env = MagicMock()
            mock_env.serpapi_key = None
            mock_settings.return_value = mock_env
            result = get_api_key("serpapi_key", None)

        assert result is None

    def test_handles_db_query_exception(self):
        from app.services.api_keys import get_api_key

        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("DB is down")

        with patch("app.services.api_keys.get_settings") as mock_settings:
            mock_env = MagicMock()
            mock_env.serpapi_key = "fallback-key"
            mock_settings.return_value = mock_env
            result = get_api_key("serpapi_key", mock_db)

        assert result == "fallback-key"

    def test_resolves_all_key_types(self):
        from app.services.api_keys import get_api_key

        key_names = [
            "serpapi_key",
            "skyscanner_api_key",
            "amadeus_client_id",
            "amadeus_client_secret",
            "seats_aero_api_key",
            "anthropic_api_key",
        ]

        for key_name in key_names:
            mock_db = MagicMock()
            settings_row = _make_settings_obj(**{key_name: f"test-{key_name}"})
            mock_db.query.return_value.filter.return_value.first.return_value = settings_row

            result = get_api_key(key_name, mock_db)
            assert result == f"test-{key_name}", f"Failed for {key_name}"

    def test_db_none_value_falls_back_to_env(self):
        from app.services.api_keys import get_api_key

        mock_db = MagicMock()
        settings_row = _make_settings_obj(serpapi_key=None)
        mock_db.query.return_value.filter.return_value.first.return_value = settings_row

        with patch("app.services.api_keys.get_settings") as mock_settings:
            mock_env = MagicMock()
            mock_env.serpapi_key = "env-fallback"
            mock_settings.return_value = mock_env
            result = get_api_key("serpapi_key", mock_db)

        assert result == "env-fallback"


class TestGetAllApiKeys:
    """Test get_all_api_keys returns all keys."""

    def test_returns_dict_with_all_keys(self):
        from app.services.api_keys import get_all_api_keys

        with patch("app.services.api_keys.get_settings") as mock_settings:
            mock_env = MagicMock()
            mock_env.serpapi_key = "s1"
            mock_env.skyscanner_api_key = None
            mock_env.amadeus_client_id = "a1"
            mock_env.amadeus_client_secret = "a2"
            mock_env.seats_aero_api_key = None
            mock_env.anthropic_api_key = "ant1"
            mock_settings.return_value = mock_env

            result = get_all_api_keys(None)

        assert "serpapi_key" in result
        assert "skyscanner_api_key" in result
        assert "amadeus_client_id" in result
        assert "amadeus_client_secret" in result
        assert "seats_aero_api_key" in result
        assert "anthropic_api_key" in result
        assert result["serpapi_key"] == "s1"
        assert result["skyscanner_api_key"] is None
