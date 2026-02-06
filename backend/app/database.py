from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

db_url = settings.database_url

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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_col_type(col) -> str:
    """Convert a SQLAlchemy column type to a SQLite type string."""
    type_name = type(col.type).__name__
    type_map = {
        "Integer": "INTEGER",
        "Float": "REAL",
        "Boolean": "BOOLEAN",
        "DateTime": "DATETIME",
        "Text": "TEXT",
        "String": f"VARCHAR({col.type.length})" if hasattr(col.type, 'length') and col.type.length else "TEXT",
        "Enum": f"VARCHAR(50)",
    }
    return type_map.get(type_name, "TEXT")


def _sqlite_default(col) -> str:
    """Extract a DEFAULT clause from a SQLAlchemy column, or empty string."""
    if col.default is not None and col.default.arg is not None:
        val = col.default.arg
        if callable(val):
            return ""
        if isinstance(val, bool):
            return f" DEFAULT {1 if val else 0}"
        if isinstance(val, (int, float)):
            return f" DEFAULT {val}"
        if isinstance(val, str):
            escaped = val.replace("'", "''")
            return f" DEFAULT '{escaped}'"
        if hasattr(val, 'value'):
            escaped = str(val.value).replace("'", "''")
            return f" DEFAULT '{escaped}'"
    return ""


def ensure_sqlite_columns():
    """Add any missing columns to SQLite tables.

    Auto-generates migration list from SQLAlchemy model metadata.
    No manual column list needed — new model columns are handled automatically.
    """
    added = 0
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            try:
                result = conn.execute(text(f"PRAGMA table_info({table.name})")).fetchall()
            except Exception:
                continue
            existing_cols = {r[1] for r in result}

            for col in table.columns:
                if col.name in existing_cols:
                    continue

                col_type = _sqlite_col_type(col)
                nullable = "" if col.nullable else " NOT NULL"
                default = _sqlite_default(col)

                # NOT NULL without DEFAULT is invalid for ALTER TABLE ADD COLUMN in SQLite
                if nullable == " NOT NULL" and not default:
                    default = _sqlite_default_for_type(col_type)

                ddl = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}{nullable}{default}"
                try:
                    conn.execute(text(ddl))
                    logger.info(f"Added column {table.name}.{col.name}")
                    added += 1
                except Exception as e:
                    logger.debug(f"Migration check for {table.name}.{col.name}: {e}")

        conn.commit()

    if added:
        logger.info(f"Schema migration: added {added} column(s)")


def _sqlite_default_for_type(col_type: str) -> str:
    """Provide a safe default for NOT NULL columns without explicit defaults."""
    if "INT" in col_type:
        return " DEFAULT 0"
    if col_type == "REAL":
        return " DEFAULT 0.0"
    if col_type == "BOOLEAN":
        return " DEFAULT 0"
    return " DEFAULT ''"
