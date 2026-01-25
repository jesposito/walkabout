from sqlalchemy import create_engine, text
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
        ("trip_plans", "search_in_progress", "BOOLEAN DEFAULT 0"),
        ("trip_plans", "search_started_at", "DATETIME"),
        ("trip_plans", "last_search_at", "DATETIME"),
        ("search_definitions", "preferred_source", "VARCHAR(20) DEFAULT 'auto'"),
        ("user_settings", "home_airports", "TEXT DEFAULT '[]'"),
        ("user_settings", "ai_provider", "VARCHAR(20) DEFAULT 'none'"),
        ("user_settings", "ai_api_key", "VARCHAR(200)"),
        ("user_settings", "ai_ollama_url", "VARCHAR(200)"),
        ("user_settings", "ai_model", "VARCHAR(50)"),
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
