from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

db_url = settings.database_url
is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )

    # Enable foreign key constraints for SQLite
    # Without this, ON DELETE CASCADE doesn't work!
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_columns():
    """Add any missing columns to SQLite tables (SQLite doesn't support full ALTER TABLE)."""
    if not is_sqlite:
        return
    
    migrations = [
        ("deals", "is_relevant", "BOOLEAN DEFAULT 1"),
        ("deals", "relevance_reason", "TEXT"),
        ("deals", "score", "INTEGER DEFAULT 0"),
        # Deal rating columns
        ("deals", "market_price", "REAL"),
        ("deals", "market_currency", "VARCHAR(3)"),
        ("deals", "deal_rating", "REAL"),
        ("deals", "rating_label", "VARCHAR(20)"),
        ("deals", "market_price_source", "VARCHAR(50)"),
        ("deals", "market_price_checked_at", "DATETIME"),
        ("trip_plans", "legs", "TEXT DEFAULT '[]'"),
        ("trip_plans", "search_in_progress", "BOOLEAN DEFAULT 0"),
        ("trip_plans", "search_started_at", "DATETIME"),
        ("trip_plans", "last_search_at", "DATETIME"),
        ("search_definitions", "preferred_source", "VARCHAR(20) DEFAULT 'auto'"),
        ("user_settings", "home_airports", "TEXT DEFAULT '[]'"),
        ("user_settings", "ai_provider", "VARCHAR(20) DEFAULT 'none'"),
        ("user_settings", "ai_api_key", "VARCHAR(200)"),
        ("user_settings", "ai_ollama_url", "VARCHAR(200)"),
        ("user_settings", "ai_model", "VARCHAR(50)"),
        # Base notification settings
        ("user_settings", "notifications_enabled", "BOOLEAN DEFAULT 0"),
        ("user_settings", "notification_min_discount_percent", "INTEGER DEFAULT 20"),
        ("user_settings", "last_notified_deal_id", "INTEGER"),
        # Notification provider settings (migration 003)
        ("user_settings", "notification_provider", "VARCHAR(20) DEFAULT 'none'"),
        ("user_settings", "notification_ntfy_url", "VARCHAR(200)"),
        ("user_settings", "notification_ntfy_topic", "VARCHAR(100)"),
        ("user_settings", "notification_discord_webhook", "VARCHAR(300)"),
        ("user_settings", "notification_quiet_hours_start", "INTEGER"),
        ("user_settings", "notification_quiet_hours_end", "INTEGER"),
        ("user_settings", "notification_cooldown_minutes", "INTEGER DEFAULT 60"),
        ("user_settings", "timezone", "VARCHAR(50) DEFAULT 'Pacific/Auckland'"),
        # Granular notification settings (migration 004)
        ("user_settings", "notify_deals", "BOOLEAN DEFAULT 1"),
        ("user_settings", "notify_trip_matches", "BOOLEAN DEFAULT 1"),
        ("user_settings", "notify_route_updates", "BOOLEAN DEFAULT 1"),
        ("user_settings", "notify_system", "BOOLEAN DEFAULT 1"),
        ("user_settings", "deal_notify_min_rating", "INTEGER DEFAULT 3"),
        ("user_settings", "deal_notify_categories", "TEXT DEFAULT '[\"local\", \"regional\"]'"),
        ("user_settings", "deal_notify_cabin_classes", "TEXT DEFAULT '[\"economy\", \"premium_economy\", \"business\", \"first\"]'"),
        ("user_settings", "deal_cooldown_minutes", "INTEGER DEFAULT 60"),
        ("user_settings", "trip_cooldown_hours", "INTEGER DEFAULT 6"),
        ("user_settings", "route_cooldown_hours", "INTEGER DEFAULT 24"),
        ("user_settings", "daily_digest_enabled", "BOOLEAN DEFAULT 0"),
        ("user_settings", "daily_digest_hour", "INTEGER DEFAULT 8"),
        # Price anomaly guard (migration 005)
        ("flight_prices", "confidence", "REAL"),
        ("flight_prices", "is_suspicious", "BOOLEAN DEFAULT 0"),
        # Semantic price context (migration 006)
        ("flight_prices", "total_price_nzd", "REAL"),
        ("flight_prices", "passengers", "INTEGER"),
        ("flight_prices", "trip_type", "VARCHAR(20)"),
        ("flight_prices", "layover_airports", "VARCHAR(200)"),
    ]
    
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            try:
                result = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                existing_cols = [r[1] for r in result]
                if column not in existing_cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                    logger.info(f"Added column {table}.{column}")
            except Exception as e:
                logger.debug(f"Migration check for {table}.{column}: {e}")
        conn.commit()
