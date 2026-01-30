"""
Test fixtures for Walkabout backend tests.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.main import app


# Create test database engine (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# Enable foreign key constraints for SQLite
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    Creates all tables before the test and drops them after.
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """
    Override the get_db dependency to use the test database session.
    """
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    return _override_get_db


@pytest.fixture(scope="function")
async def client(override_get_db):
    """
    Create an async test client with the database dependency overridden.
    """
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clear overrides after test
    app.dependency_overrides.clear()
