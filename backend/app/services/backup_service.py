"""SQLite backup service using Python's sqlite3.Connection.backup() for safe online backups."""

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_backup_dir() -> Path:
    """Get the backup directory path, creating it if needed."""
    settings = get_settings()
    # Database URL is like sqlite:///./data/walkabout.db
    # Data dir is the parent of the database file
    db_path = settings.database_url.replace("sqlite:///", "")
    data_dir = Path(db_path).parent
    backup_dir = data_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_db_path() -> str:
    """Get the actual filesystem path to the SQLite database."""
    settings = get_settings()
    return settings.database_url.replace("sqlite:///", "")


def create_backup(max_backups: int = 7) -> dict:
    """Create a backup of the SQLite database.

    Uses sqlite3.Connection.backup() for a safe, consistent backup
    even while the database is being written to.

    Args:
        max_backups: Maximum number of backup files to keep. Oldest are deleted.

    Returns:
        Dict with backup path, size, and status.
    """
    db_path = get_db_path()
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"walkabout-{timestamp}.db"

    try:
        source = sqlite3.connect(db_path)
        dest = sqlite3.connect(str(backup_path))

        source.backup(dest)

        dest.close()
        source.close()

        size_bytes = backup_path.stat().st_size
        logger.info(f"Backup created: {backup_path} ({size_bytes:,} bytes)")

        # Rotate old backups
        _rotate_backups(backup_dir, max_backups)

        return {
            "status": "ok",
            "path": str(backup_path),
            "size_bytes": size_bytes,
            "timestamp": timestamp,
        }

    except Exception as e:
        logger.error(f"Backup failed: {e}")
        # Clean up partial backup
        if backup_path.exists():
            backup_path.unlink()
        return {
            "status": "error",
            "error": str(e),
        }


def _rotate_backups(backup_dir: Path, max_backups: int):
    """Delete oldest backups beyond max_backups count."""
    backups = sorted(backup_dir.glob("walkabout-*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) > max_backups:
        oldest = backups.pop(0)
        oldest.unlink()
        logger.info(f"Rotated old backup: {oldest.name}")


def list_backups() -> list[dict]:
    """List all existing backups with metadata."""
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("walkabout-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {
            "filename": b.name,
            "size_bytes": b.stat().st_size,
            "created_at": datetime.fromtimestamp(b.stat().st_mtime).isoformat(),
        }
        for b in backups
    ]
