from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://walkabout:walkabout_dev@localhost:5432/walkabout"
    redis_url: str = "redis://localhost:6379/0"
    
    seats_aero_api_key: str = ""
    anthropic_api_key: str = ""
    
    ntfy_url: str = "http://localhost:8080"
    ntfy_topic: str = "walkabout-deals"
    
    scrape_frequency_hours: int = 12
    deal_threshold_z_score: float = -1.5
    min_history_for_analysis: int = 10
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
