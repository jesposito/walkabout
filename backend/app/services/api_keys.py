"""
Centralized API key resolution.

Keys are resolved in order:
1. UserSettings database (user-configured via UI)
2. Environment variables (deployment-configured via .env)

This ensures UI-entered keys actually work while maintaining
backward compatibility with env-var-only deployments.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.config import get_settings

logger = logging.getLogger(__name__)

# Map of key names to their env var setting attribute names
_KEY_MAP = {
    "serpapi_key": "serpapi_key",
    "skyscanner_api_key": "skyscanner_api_key",
    "amadeus_client_id": "amadeus_client_id",
    "amadeus_client_secret": "amadeus_client_secret",
    "seats_aero_api_key": "seats_aero_api_key",
    "anthropic_api_key": "anthropic_api_key",
}


def get_api_key(key_name: str, db: Optional[Session] = None) -> Optional[str]:
    """
    Resolve an API key by checking UserSettings DB first, then env vars.

    Args:
        key_name: The key name (e.g., "serpapi_key", "amadeus_client_id")
        db: Optional database session. If provided, checks UserSettings first.

    Returns:
        The API key string, or None if not configured anywhere.
    """
    # 1. Check UserSettings database
    if db is not None:
        try:
            from app.models.user_settings import UserSettings
            settings = db.query(UserSettings).filter(UserSettings.id == 1).first()
            if settings:
                db_value = getattr(settings, key_name, None)
                if db_value and isinstance(db_value, str) and db_value.strip():
                    return db_value.strip()
        except Exception as e:
            logger.debug(f"Could not read {key_name} from DB: {e}")

    # 2. Fall back to environment variable
    env_settings = get_settings()
    env_attr = _KEY_MAP.get(key_name, key_name)
    env_value = getattr(env_settings, env_attr, None)
    if env_value and isinstance(env_value, str) and env_value.strip():
        return env_value.strip()

    return None


def get_all_api_keys(db: Optional[Session] = None) -> dict[str, Optional[str]]:
    """Get all API keys with DB-first resolution. Useful for status checks."""
    return {name: get_api_key(name, db) for name in _KEY_MAP}
