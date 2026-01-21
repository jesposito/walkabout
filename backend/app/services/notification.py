import httpx
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from app.config import get_settings
from app.models import SearchDefinition, FlightPrice

settings = get_settings()


class NtfyNotifier:
    """
    Enhanced notification service for Phase 1a.
    
    Sends notifications for:
    1. Deal alerts (price drops)
    2. System alerts (failures, stale data)
    
    Oracle Review: "ntfy alerts for deals AND system failures"
    """
    
    def __init__(self, base_url: Optional[str] = None, topic: Optional[str] = None):
        self.base_url = base_url or settings.ntfy_url or "http://ntfy:80"
        self.topic = topic or settings.ntfy_topic or "walkabout-deals"
    
    async def send_deal_alert(
        self,
        search_def: SearchDefinition,
        price: FlightPrice,
        analysis,  # DealAnalysis from price_analyzer
    ):
        """
        Send a deal alert notification.
        
        Args:
            search_def: The search definition
            price: The FlightPrice record that triggered the deal
            analysis: DealAnalysis with deal details
        """
        # Format travel dates
        dep_date = price.departure_date.strftime("%b %d")
        ret_date = price.return_date.strftime("%b %d") if price.return_date else "One-way"
        
        # Calculate savings message
        if analysis.is_new_low:
            savings_msg = f"🔥 NEW LOW! (was ${analysis.median_price})"
        else:
            savings = abs(analysis.price_vs_median)
            savings_msg = f"${savings:.0f} below median"
        
        # Priority based on how good the deal is
        if analysis.is_new_low or analysis.robust_z_score < -2.0:
            priority = "urgent"
        elif analysis.robust_z_score < -1.5:
            priority = "high"
        else:
            priority = "default"
        
        message = f"""✈️ {search_def.display_name}
📅 {dep_date} → {ret_date}
💰 ${price.price_nzd} NZD
📉 {savings_msg}
📊 {analysis.percentile:.0f}th percentile
🎯 {analysis.reason}"""
        
        if price.airline and price.airline != "Unknown":
            message += f"\n🛫 {price.airline}"
        
        if analysis.history_count >= 10:
            message += f"\n📈 Based on {analysis.history_count} price points"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/{self.topic}",
                    content=message,
                    headers={
                        "Title": f"🎉 Flight Deal: ${price.price_nzd}",
                        "Priority": priority,
                        "Tags": "airplane,moneybag,fire" if analysis.is_new_low else "airplane,moneybag",
                        "Actions": f"view, View Details, {settings.base_url or 'http://localhost:8000'}/search/{search_def.id}"
                    }
                )
                response.raise_for_status()
        except Exception as e:
            # Don't fail the entire scrape if notification fails
            import logging
            logging.error(f"Failed to send deal notification: {e}")
    
    async def send_system_alert(
        self,
        title: str,
        message: str,
        priority: str = "default"
    ):
        """
        Send a system alert (failures, health issues, etc).
        
        Args:
            title: Alert title
            message: Alert message
            priority: urgent, high, default, low, min
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/{self.topic}",
                    content=message,
                    headers={
                        "Title": title,
                        "Priority": priority,
                        "Tags": "warning,gear",
                    }
                )
                response.raise_for_status()
        except Exception as e:
            # Log error but don't raise - system alerts shouldn't break the app
            import logging
            logging.error(f"Failed to send system alert: {e}")
    
    async def send_startup_notification(self):
        """Send a notification when the system starts up."""
        await self.send_system_alert(
            title="🚀 Walkabout Started",
            message="Flight monitoring system is online and ready to track deals.",
            priority="low"
        )
    
    async def send_test_notification(self) -> bool:
        """
        Send a test notification to verify ntfy is working.
        
        Returns: True if successful, False if failed
        """
        try:
            await self.send_system_alert(
                title="🧪 Test Notification",
                message="This is a test to verify ntfy notifications are working correctly.",
                priority="min"
            )
            return True
        except Exception:
            return False
    
    def get_notification_url(self) -> str:
        """Get the ntfy web interface URL for users to subscribe."""
        return f"{self.base_url}/{self.topic}"


# Legacy function for backwards compatibility during transition
async def send_deal_alert_legacy(
    route_name: str,
    departure_date: str,
    return_date: str,
    price_nzd: Decimal,
    deal,  # DealAnalysis
    airline: str = None
):
    """
    Legacy deal alert function - kept for backwards compatibility.
    New code should use NtfyNotifier.send_deal_alert().
    """
    notifier = NtfyNotifier()
    
    # Create mock objects for compatibility
    class MockSearchDef:
        display_name = route_name
    
    class MockPrice:
        price_nzd = price_nzd
        departure_date = departure_date  # This would need proper date parsing
        return_date = return_date
        airline = airline
    
    await notifier.send_deal_alert(MockSearchDef(), MockPrice(), deal)