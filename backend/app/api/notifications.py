from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict

from app.database import get_db
from app.models.user_settings import UserSettings
from app.services.notification import get_global_notifier

router = APIRouter()


@router.get("/notifications")
async def get_notifications(limit: int = 50) -> List[Dict]:
    """Get recent notifications from history."""
    notifier = get_global_notifier()
    return notifier.get_notifications(limit=limit)


@router.post("/notifications/test")
async def test_notification(db: Session = Depends(get_db)) -> Dict:
    """Send a test notification via configured provider."""
    notifier = get_global_notifier()
    user_settings = UserSettings.get_or_create(db)

    success, message = await notifier.send_test_notification(user_settings)

    return {
        "success": success,
        "message": message,
        "provider": user_settings.notification_provider or "none",
    }


@router.delete("/notifications")
async def clear_notifications() -> Dict[str, str]:
    """Clear notification history."""
    notifier = get_global_notifier()
    notifier.clear_notifications()
    return {"status": "cleared"}
