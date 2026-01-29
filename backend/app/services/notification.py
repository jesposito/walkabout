from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict
import uuid
import logging
import httpx
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class Notification:
    """Notification record."""
    id: str
    title: str
    message: str
    priority: str
    timestamp: datetime
    type: str  # "deal", "system", or "award"
    tags: List[str]
    sent_to_ntfy: bool = False


class NotificationHistory:
    """In-memory notification history for dashboard display."""

    def __init__(self, max_notifications: int = 100):
        self._notifications: List[Notification] = []
        self._max_notifications = max_notifications

    def add(self, notification: Notification):
        self._notifications.append(notification)
        if len(self._notifications) > self._max_notifications:
            self._notifications.pop(0)

    def get_recent(self, limit: int = 50) -> List[Dict]:
        recent = self._notifications[-limit:] if limit else self._notifications
        return [asdict(n) for n in reversed(recent)]

    def clear(self):
        self._notifications.clear()


class NtfyNotifier:
    """
    Notification service that sends push notifications via ntfy.

    Features:
    - Real HTTP POST to ntfy server
    - Quiet hours support (no notifications during sleep)
    - Cooldown to prevent notification spam
    - Priority-based ntfy priorities
    - In-memory history for dashboard
    """

    # Priority mapping to ntfy priorities (1=min, 5=max)
    PRIORITY_MAP = {
        "min": "1",
        "low": "2",
        "default": "3",
        "high": "4",
        "urgent": "5",
    }

    def __init__(
        self,
        ntfy_url: Optional[str] = None,
        ntfy_topic: Optional[str] = None,
    ):
        self.ntfy_url = ntfy_url or settings.ntfy_url
        self.ntfy_topic = ntfy_topic or settings.ntfy_topic
        self.history = NotificationHistory()
        self._last_notification_time: Dict[str, datetime] = {}  # route -> last notification time
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    async def close(self):
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _is_quiet_hours(
        self,
        quiet_start: Optional[int],
        quiet_end: Optional[int],
        user_timezone: str = "Pacific/Auckland"
    ) -> bool:
        """Check if current time is within quiet hours."""
        if quiet_start is None or quiet_end is None:
            return False

        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(user_timezone))
            current_hour = now.hour

            # Handle overnight quiet hours (e.g., 22:00 - 07:00)
            if quiet_start > quiet_end:
                return current_hour >= quiet_start or current_hour < quiet_end
            else:
                return quiet_start <= current_hour < quiet_end
        except Exception as e:
            logger.warning(f"Error checking quiet hours: {e}")
            return False

    def _is_in_cooldown(
        self,
        route_key: str,
        cooldown_minutes: int = 60
    ) -> bool:
        """Check if route is still in notification cooldown."""
        if route_key not in self._last_notification_time:
            return False

        last_time = self._last_notification_time[route_key]
        cooldown_delta = timedelta(minutes=cooldown_minutes)
        return datetime.now(timezone.utc) - last_time < cooldown_delta

    def _record_notification(self, route_key: str):
        """Record notification time for cooldown tracking."""
        self._last_notification_time[route_key] = datetime.now(timezone.utc)

    async def _send_to_ntfy(
        self,
        title: str,
        message: str,
        priority: str = "default",
        tags: Optional[List[str]] = None,
        click_url: Optional[str] = None,
    ) -> bool:
        """Send notification to ntfy server."""
        try:
            client = await self._get_client()
            url = f"{self.ntfy_url}/{self.ntfy_topic}"

            headers = {
                "Title": title,
                "Priority": self.PRIORITY_MAP.get(priority, "3"),
            }

            if tags:
                headers["Tags"] = ",".join(tags)

            if click_url:
                headers["Click"] = click_url

            response = await client.post(
                url,
                content=message,
                headers=headers,
            )

            if response.status_code == 200:
                logger.info(f"Notification sent: {title}")
                return True
            else:
                logger.error(f"ntfy returned {response.status_code}: {response.text}")
                return False

        except httpx.ConnectError as e:
            logger.warning(f"Could not connect to ntfy server at {self.ntfy_url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def send_deal_alert(
        self,
        search_def,  # SearchDefinition
        price,  # FlightPrice
        analysis,  # DealAnalysis from price_analyzer
        user_settings = None,  # UserSettings for preferences
    ) -> bool:
        """
        Send deal alert notification.

        Respects quiet hours and cooldown settings from user_settings.
        """
        # Check if notifications are enabled
        if user_settings and not getattr(user_settings, 'notifications_enabled', True):
            logger.debug("Notifications disabled by user")
            return False

        # Check quiet hours
        if user_settings:
            quiet_start = getattr(user_settings, 'notification_quiet_hours_start', None)
            quiet_end = getattr(user_settings, 'notification_quiet_hours_end', None)
            user_tz = getattr(user_settings, 'timezone', 'Pacific/Auckland')

            if self._is_quiet_hours(quiet_start, quiet_end, user_tz):
                logger.debug("Skipping notification during quiet hours")
                return False

        # Check cooldown
        route_key = f"{search_def.origin}-{search_def.destination}"
        cooldown = getattr(user_settings, 'notification_cooldown_minutes', 60) if user_settings else 60

        if self._is_in_cooldown(route_key, cooldown):
            logger.debug(f"Skipping notification for {route_key} - in cooldown")
            return False

        # Build notification content
        dep_date = price.departure_date.strftime("%b %d")
        return_date_val = getattr(price, 'return_date', None)
        ret_date = return_date_val.strftime("%b %d") if return_date_val else "One-way"

        if analysis.is_new_low:
            savings_msg = f"NEW LOW! (was ${analysis.median_price})"
            tags = ["airplane", "fire"]
        else:
            savings = abs(analysis.price_vs_median)
            savings_msg = f"${savings:.0f} below median"
            tags = ["airplane", "moneybag"]

        if analysis.is_new_low or analysis.robust_z_score < -2.0:
            priority = "urgent"
        elif analysis.robust_z_score < -1.5:
            priority = "high"
        else:
            priority = "default"

        title = f"✈️ ${price.price_nzd} {search_def.origin}→{search_def.destination}"

        message = f"{search_def.display_name}\n"
        message += f"📅 {dep_date} → {ret_date}\n"
        message += f"💰 ${price.price_nzd} NZD ({savings_msg})\n"
        message += f"📊 {analysis.percentile:.0f}th percentile\n"
        message += f"📝 {analysis.reason}"

        airline_val = getattr(price, 'airline', None)
        if airline_val and str(airline_val) != "Unknown":
            message += f"\n✈️ {airline_val}"

        # Send to ntfy
        sent = await self._send_to_ntfy(
            title=title,
            message=message,
            priority=priority,
            tags=tags,
            click_url=f"{settings.base_url}/deals",
        )

        # Record in history
        notification = Notification(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            priority=priority,
            timestamp=datetime.now(timezone.utc),
            type="deal",
            tags=tags,
            sent_to_ntfy=sent,
        )
        self.history.add(notification)

        # Record cooldown
        if sent:
            self._record_notification(route_key)

        return sent

    async def send_system_alert(
        self,
        title: str,
        message: str,
        priority: str = "default",
        alert_type: str = "info",  # info, warning, error
    ) -> bool:
        """Send system alert (failures, stale data, etc.)."""
        tag_map = {
            "info": ["information_source"],
            "warning": ["warning"],
            "error": ["rotating_light", "x"],
        }
        tags = tag_map.get(alert_type, ["bell"])

        sent = await self._send_to_ntfy(
            title=f"🔧 {title}",
            message=message,
            priority=priority,
            tags=tags,
            click_url=f"{settings.base_url}/status",
        )

        notification = Notification(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            priority=priority,
            timestamp=datetime.now(timezone.utc),
            type="system",
            tags=tags,
            sent_to_ntfy=sent,
        )
        self.history.add(notification)

        return sent

    async def send_scrape_failure_alert(
        self,
        route: str,
        failure_reason: str,
        consecutive_failures: int,
    ) -> bool:
        """Send alert when scraping fails repeatedly."""
        if consecutive_failures < 3:
            return False  # Only alert after 3+ failures

        priority = "high" if consecutive_failures >= 5 else "default"

        return await self.send_system_alert(
            title=f"Scrape Failure: {route}",
            message=f"Google Flights scraping failed {consecutive_failures}x.\nReason: {failure_reason}",
            priority=priority,
            alert_type="warning" if consecutive_failures < 5 else "error",
        )

    async def send_stale_data_alert(
        self,
        route: str,
        hours_since_update: float,
    ) -> bool:
        """Send alert when price data is stale."""
        return await self.send_system_alert(
            title=f"Stale Data: {route}",
            message=f"No price updates for {hours_since_update:.1f} hours.",
            priority="default",
            alert_type="warning",
        )

    async def send_circuit_open_alert(
        self,
        route: str,
    ) -> bool:
        """Send alert when circuit breaker opens."""
        return await self.send_system_alert(
            title=f"Circuit Open: {route}",
            message="Scraping paused due to repeated failures. Will retry automatically.",
            priority="high",
            alert_type="error",
        )

    async def send_startup_notification(self) -> bool:
        """Send notification when system starts."""
        return await self.send_system_alert(
            title="Walkabout Started",
            message="Flight monitoring system is online and ready to track deals.",
            priority="low",
            alert_type="info",
        )

    async def send_test_notification(self) -> bool:
        """Send test notification to verify ntfy connection."""
        return await self._send_to_ntfy(
            title="🧪 Test Notification",
            message="If you see this, notifications are working correctly!",
            priority="default",
            tags=["white_check_mark", "test_tube"],
        )

    def get_notifications(self, limit: int = 50) -> List[Dict]:
        """Get recent notifications for dashboard."""
        return self.history.get_recent(limit)

    def clear_notifications(self):
        """Clear notification history."""
        self.history.clear()

    def get_notification_url(self) -> str:
        """Get ntfy subscription URL."""
        return f"{self.ntfy_url}/{self.ntfy_topic}"


# Legacy alias for backward compatibility
InMemoryNotifier = NtfyNotifier

# Create global notifier instance
_global_notifier: Optional[NtfyNotifier] = None


def get_global_notifier() -> NtfyNotifier:
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = NtfyNotifier()
    return _global_notifier


async def shutdown_notifier():
    """Close the global notifier's HTTP client."""
    global _global_notifier
    if _global_notifier is not None:
        await _global_notifier.close()
