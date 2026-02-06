from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.services.backup_service import create_backup, list_backups

router = APIRouter()


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status
    }


@router.post("/api/backup")
async def trigger_backup():
    """Create an on-demand SQLite backup."""
    result = create_backup()
    return result


@router.get("/api/backups")
async def get_backups():
    """List all available backups."""
    return list_backups()
