from fastapi import APIRouter
from typing import List, Dict
from app.services.notification import get_global_notifier

router = APIRouter()


@router.get("/notifications")
async def get_notifications(limit: int = 50) -> List[Dict]:
    notifier = get_global_notifier()
    return notifier.get_notifications(limit=limit)


@router.post("/notifications/test")
async def test_notification() -> Dict[str, bool]:
    notifier = get_global_notifier()
    success = await notifier.send_test_notification()
    return {"success": success}


@router.delete("/notifications")
async def clear_notifications() -> Dict[str, str]:
    notifier = get_global_notifier()
    notifier.clear_notifications()
    return {"status": "cleared"}