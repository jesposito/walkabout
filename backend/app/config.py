from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    env: str = "dev"
    database_url: str = "sqlite:///./data/walkabout.db"
    
    scheduler_enabled: bool = True
    scrape_frequency_hours: int = 12
    
    seats_aero_api_key: str = ""
    anthropic_api_key: str = ""
    
    ntfy_url: str = "http://localhost:8080"
    ntfy_topic: str = "walkabout-deals"
    base_url: str = "http://localhost:8000"
    
    deal_threshold_z_score: float = -1.5
    min_history_for_analysis: int = 10
    
    def model_post_init(self, __context):
        if self.env == "prod" and self.database_url.startswith("sqlite"):
            raise ValueError(
                "Production requires explicit DATABASE_URL (not SQLite)"
            )
    
    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
