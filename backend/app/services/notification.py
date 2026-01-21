from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict
import uuid
import logging
from app.config import get_settings
from app.models import SearchDefinition, FlightPrice

settings = get_settings()


@dataclass
class Notification:
    """In-memory notification record for Phase 1a."""
    id: str
    title: str
    message: str
    priority: str
    timestamp: datetime
    type: str  # "deal" or "system"
    tags: List[str]


class InMemoryNotifier:
    """
    In-memory notification service for Phase 1a single-container deployment.
    
    Stores notifications in memory instead of external ntfy server.
    Provides API endpoints to view notifications via the dashboard.
    
    Notifications for:
    1. Deal alerts (price drops)
    2. System alerts (failures, stale data)
    """
    
    def __init__(self):
        self._notifications: List[Notification] = []
        self._max_notifications = 100  # Keep last 100 notifications
    
    def _add_notification(self, notification: Notification):
        self._notifications.append(notification)
        if len(self._notifications) > self._max_notifications:
            self._notifications.pop(0)
    
    def get_notifications(self, limit: int = 50) -> List[Dict]:
        recent_notifications = self._notifications[-limit:] if limit else self._notifications
        return [asdict(notification) for notification in reversed(recent_notifications)]
    
    def clear_notifications(self):
        self._notifications.clear()
    
    async def send_deal_alert(
        self,
        search_def: SearchDefinition,
        price: FlightPrice,
        analysis,  # DealAnalysis from price_analyzer
    ):
        dep_date = price.departure_date.strftime("%b %d")
        return_date_val = getattr(price, 'return_date', None)
        ret_date = return_date_val.strftime("%b %d") if return_date_val else "One-way"
        
        if analysis.is_new_low:
            savings_msg = f"NEW LOW! (was ${analysis.median_price})"
        else:
            savings = abs(analysis.price_vs_median)
            savings_msg = f"${savings:.0f} below median"
        
        if analysis.is_new_low or analysis.robust_z_score < -2.0:
            priority = "urgent"
        elif analysis.robust_z_score < -1.5:
            priority = "high"
        else:
            priority = "default"
        
        message = f"Flight Deal: {search_def.display_name}\n"
        message += f"Travel: {dep_date} → {ret_date}\n"
        message += f"Price: ${price.price_nzd} NZD\n"
        message += f"Deal: {savings_msg}\n"
        message += f"Percentile: {analysis.percentile:.0f}th\n"
        message += f"Reason: {analysis.reason}"
        
        airline_val = getattr(price, 'airline', None)
        if airline_val and str(airline_val) != "Unknown":
            message += f"\nAirline: {airline_val}"
        
        if analysis.history_count >= 10:
            message += f"\nBased on {analysis.history_count} price points"
        
        notification = Notification(
            id=str(uuid.uuid4()),
            title=f"Flight Deal: ${price.price_nzd}",
            message=message,
            priority=priority,
            timestamp=datetime.now(timezone.utc),
            type="deal",
            tags=["airplane", "deal"] + (["fire"] if analysis.is_new_low else [])
        )
        
        self._add_notification(notification)
    async def send_system_alert(
        self,
        title: str,
        message: str,
        priority: str = "default"
    ):
        try:
            notification = Notification(
                id=str(uuid.uuid4()),
                title=title,
                message=message,
                priority=priority,
                timestamp=datetime.now(timezone.utc),
                type="system",
                tags=["system", "alert"]
            )
            
            self._add_notification(notification)
            logging.info(f"System alert: {title}")
            
        except Exception as e:
            logging.error(f"Failed to send system alert: {e}")
    
    async def send_startup_notification(self):
        await self.send_system_alert(
            title="Walkabout Started",
            message="Flight monitoring system is online and ready to track deals.",
            priority="low"
        )
    
    async def send_test_notification(self) -> bool:
        try:
            await self.send_system_alert(
                title="Test Notification",
                message="This is a test to verify notifications are working correctly.",
                priority="min"
            )
            return True
        except Exception:
            return False
    
    def get_notification_url(self) -> str:
        return "/api/notifications"


# Alias for backwards compatibility
NtfyNotifier = InMemoryNotifier

# Create global notifier instance
_global_notifier = InMemoryNotifier()

def get_global_notifier() -> InMemoryNotifier:
    return _global_notifier