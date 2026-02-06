"""
Multi-provider notification service.

Supports:
- none: In-app history only (no push notifications)
- ntfy_self: Self-hosted ntfy server
- ntfy_sh: Public ntfy.sh service
- discord: Discord webhook
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import uuid
import logging
import json
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
    sent: bool = False
    provider: str = "none"


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


class NotificationService:
    """
    Multi-provider notification service.

    Providers:
    - none: In-app history only
    - ntfy_self: Self-hosted ntfy (user provides URL)
    - ntfy_sh: Public ntfy.sh service
    - discord: Discord webhook

    Features:
    - Quiet hours support
    - Cooldown to prevent spam
    - In-memory history for dashboard
    - Graceful degradation (always records to history)
    """

    NTFY_PRIORITY_MAP = {
        "min": "1",
        "low": "2",
        "default": "3",
        "high": "4",
        "urgent": "5",
    }

    def __init__(self):
        self.history = NotificationHistory()
        self._last_notification_time: Dict[str, datetime] = {}
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
        user_timezone: str = "America/New_York"
    ) -> bool:
        """Check if current time is within quiet hours."""
        if quiet_start is None or quiet_end is None:
            return False

        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(user_timezone))
            current_hour = now.hour

            if quiet_start > quiet_end:
                return current_hour >= quiet_start or current_hour < quiet_end
            else:
                return quiet_start <= current_hour < quiet_end
        except Exception as e:
            logger.warning(f"Error checking quiet hours: {e}")
            return False

    def _is_in_cooldown(self, route_key: str, cooldown_minutes: int = 60) -> bool:
        """Check if route is still in notification cooldown."""
        if route_key not in self._last_notification_time:
            return False

        last_time = self._last_notification_time[route_key]
        cooldown_delta = timedelta(minutes=cooldown_minutes)
        return datetime.now(timezone.utc) - last_time < cooldown_delta

    def _record_notification(self, route_key: str):
        """Record notification time for cooldown tracking."""
        self._last_notification_time[route_key] = datetime.now(timezone.utc)

    # --- Provider-specific send methods ---

    async def _send_ntfy(
        self,
        url: str,
        topic: str,
        title: str,
        message: str,
        priority: str = "default",
        tags: Optional[List[str]] = None,
        click_url: Optional[str] = None,
    ) -> bool:
        """Send to ntfy server (self-hosted or ntfy.sh)."""
        try:
            client = await self._get_client()
            endpoint = f"{url.rstrip('/')}"

            # Use JSON API to properly handle UTF-8/emoji in title and message
            payload = {
                "topic": topic,
                "title": title,
                "message": message,
                "priority": int(self.NTFY_PRIORITY_MAP.get(priority, "3")),
            }

            if tags:
                payload["tags"] = tags
            if click_url:
                payload["click"] = click_url

            response = await client.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                logger.info(f"ntfy notification sent: {title}")
                return True
            else:
                logger.error(f"ntfy returned {response.status_code}: {response.text}")
                return False

        except httpx.ConnectError as e:
            logger.warning(f"Could not connect to ntfy at {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"ntfy send failed: {e}")
            return False

    async def _send_discord(
        self,
        webhook_url: str,
        title: str,
        message: str,
        priority: str = "default",
        color: Optional[int] = None,
    ) -> bool:
        """Send to Discord webhook."""
        try:
            client = await self._get_client()

            # Color based on priority
            if color is None:
                color_map = {
                    "urgent": 0xFF0000,  # Red
                    "high": 0xFFA500,    # Orange
                    "default": 0x00FF00, # Green
                    "low": 0x808080,     # Gray
                    "min": 0x808080,
                }
                color = color_map.get(priority, 0x00FF00)

            payload = {
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": color,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }]
            }

            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code in (200, 204):
                logger.info(f"Discord notification sent: {title}")
                return True
            else:
                logger.error(f"Discord returned {response.status_code}: {response.text}")
                return False

        except httpx.ConnectError as e:
            logger.warning(f"Could not connect to Discord: {e}")
            return False
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
            return False

    # --- Main send method ---

    async def _send(
        self,
        title: str,
        message: str,
        priority: str = "default",
        tags: Optional[List[str]] = None,
        click_url: Optional[str] = None,
        user_settings=None,
    ) -> tuple[bool, str]:
        """
        Send notification via configured provider.

        Returns: (success, provider_used)
        """
        if user_settings is None:
            return False, "none"

        provider = getattr(user_settings, 'notification_provider', 'none') or 'none'

        if provider == "none":
            return False, "none"

        elif provider == "ntfy_self":
            url = getattr(user_settings, 'notification_ntfy_url', None)
            topic = getattr(user_settings, 'notification_ntfy_topic', None)

            if not url or not topic:
                logger.warning("ntfy_self selected but URL/topic not configured")
                return False, "ntfy_self"

            success = await self._send_ntfy(url, topic, title, message, priority, tags, click_url)
            return success, "ntfy_self"

        elif provider == "ntfy_sh":
            topic = getattr(user_settings, 'notification_ntfy_topic', None)

            if not topic:
                logger.warning("ntfy_sh selected but topic not configured")
                return False, "ntfy_sh"

            success = await self._send_ntfy("https://ntfy.sh", topic, title, message, priority, tags, click_url)
            return success, "ntfy_sh"

        elif provider == "discord":
            webhook = getattr(user_settings, 'notification_discord_webhook', None)

            if not webhook:
                logger.warning("discord selected but webhook not configured")
                return False, "discord"

            success = await self._send_discord(webhook, title, message, priority)
            return success, "discord"

        else:
            logger.warning(f"Unknown provider: {provider}")
            return False, provider

    # --- Public notification methods ---

    async def send_deal_alert(
        self,
        search_def,
        price,
        analysis,
        user_settings=None,
    ) -> bool:
        """Send deal alert notification."""
        if user_settings is None:
            return False

        if not getattr(user_settings, 'notifications_enabled', False):
            logger.debug("Notifications disabled")
            return False

        # Check quiet hours
        quiet_start = getattr(user_settings, 'notification_quiet_hours_start', None)
        quiet_end = getattr(user_settings, 'notification_quiet_hours_end', None)
        user_tz = getattr(user_settings, 'timezone', 'America/New_York')

        if self._is_quiet_hours(quiet_start, quiet_end, user_tz):
            logger.debug("Skipping notification during quiet hours")
            return False

        # Check cooldown
        route_key = f"{search_def.origin}-{search_def.destination}"
        cooldown = getattr(user_settings, 'notification_cooldown_minutes', 60) or 60

        if self._is_in_cooldown(route_key, cooldown):
            logger.debug(f"Skipping {route_key} - in cooldown")
            return False

        # Build content
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

        currency = getattr(search_def, 'currency', 'USD') or 'USD'
        title = f"✈️ ${price.price_nzd} {currency} {search_def.origin}→{search_def.destination}"

        message = f"{search_def.display_name}\n"
        message += f"📅 {dep_date} → {ret_date}\n"
        message += f"💰 ${price.price_nzd} {currency} ({savings_msg})\n"
        message += f"📊 {analysis.percentile:.0f}th percentile"

        airline_val = getattr(price, 'airline', None)
        if airline_val and str(airline_val) != "Unknown":
            message += f"\n✈️ {airline_val}"

        # Send via provider
        sent, provider = await self._send(
            title=title,
            message=message,
            priority=priority,
            tags=tags,
            click_url=f"{settings.base_url}/deals",
            user_settings=user_settings,
        )

        # Always record to history
        notification = Notification(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            priority=priority,
            timestamp=datetime.now(timezone.utc),
            type="deal",
            tags=tags,
            sent=sent,
            provider=provider,
        )
        self.history.add(notification)

        if sent:
            self._record_notification(route_key)

        return sent

    async def send_system_alert(
        self,
        title: str,
        message: str,
        priority: str = "default",
        alert_type: str = "info",
        user_settings=None,
    ) -> bool:
        """Send system alert."""
        tag_map = {
            "info": ["information_source"],
            "warning": ["warning"],
            "error": ["rotating_light"],
        }
        tags = tag_map.get(alert_type, ["bell"])

        sent, provider = await self._send(
            title=f"🔧 {title}",
            message=message,
            priority=priority,
            tags=tags,
            click_url=f"{settings.base_url}/status",
            user_settings=user_settings,
        )

        notification = Notification(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            priority=priority,
            timestamp=datetime.now(timezone.utc),
            type="system",
            tags=tags,
            sent=sent,
            provider=provider,
        )
        self.history.add(notification)

        return sent

    async def send_startup_notification(self, user_settings=None) -> bool:
        """Send startup notification."""
        return await self.send_system_alert(
            title="Walkabout Started",
            message="Flight monitoring system is online.",
            priority="low",
            alert_type="info",
            user_settings=user_settings,
        )

    async def send_test_notification(self, user_settings=None) -> tuple[bool, str]:
        """
        Send test notification.

        Returns: (success, message)
        """
        if user_settings is None:
            return False, "No settings provided"

        provider = getattr(user_settings, 'notification_provider', 'none') or 'none'

        if provider == "none":
            return False, "No provider configured. Select a notification method in settings."

        sent, used_provider = await self._send(
            title="🧪 Test Notification",
            message="If you see this, notifications are working!",
            priority="default",
            tags=["white_check_mark"],
            user_settings=user_settings,
        )

        if sent:
            return True, f"Sent via {used_provider}"
        else:
            return False, f"Failed to send via {used_provider}. Check your configuration."

    def get_notifications(self, limit: int = 50) -> List[Dict]:
        """Get recent notifications for dashboard."""
        return self.history.get_recent(limit)

    def clear_notifications(self):
        """Clear notification history."""
        self.history.clear()


# Aliases for backward compatibility
NtfyNotifier = NotificationService
InMemoryNotifier = NotificationService

# Global instance
_global_notifier: Optional[NotificationService] = None


def get_global_notifier() -> NotificationService:
    global _global_notifier
    if _global_notifier is None:
        _global_notifier = NotificationService()
    return _global_notifier


async def shutdown_notifier():
    """Close the global notifier's HTTP client."""
    global _global_notifier
    if _global_notifier is not None:
        await _global_notifier.close()
