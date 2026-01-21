from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# SQLite needs different configuration than PostgreSQL
db_url = settings.database_url
is_sqlite = db_url.startswith("sqlite")

if is_sqlite:
    # SQLite: no pooling, enable check_same_thread=False for FastAPI
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL: use connection pooling
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
