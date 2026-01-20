import httpx
from dataclasses import dataclass
from decimal import Decimal
from app.config import get_settings

settings = get_settings()


@dataclass
class DealAnalysis:
    is_deal: bool
    z_score: float
    mean_price: Decimal
    price_vs_mean: Decimal
    percentile: float
    reason: str = ""


class NtfyNotifier:
    def __init__(self, base_url: str = None, topic: str = None):
        self.base_url = base_url or settings.ntfy_url
        self.topic = topic or settings.ntfy_topic
    
    async def send_deal_alert(
        self,
        route_name: str,
        departure_date: str,
        return_date: str,
        price_nzd: Decimal,
        deal: DealAnalysis,
        airline: str = None
    ):
        savings = abs(deal.price_vs_mean)
        priority = "urgent" if deal.z_score < -2.0 else "high"
        
        message = f"""
{route_name}
{departure_date} - {return_date}

${price_nzd:.0f} NZD
${savings:.0f} below average
Better than {deal.percentile:.0f}% of prices
"""
        if airline:
            message += f"\n{airline}"
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/{self.topic}",
                content=message.strip(),
                headers={
                    "Title": f"Flight Deal: ${price_nzd:.0f}",
                    "Priority": priority,
                    "Tags": "airplane,moneybag",
                }
            )
    
    async def send_system_alert(self, title: str, message: str, priority: str = "default"):
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/{self.topic}",
                content=message,
                headers={
                    "Title": title,
                    "Priority": priority,
                    "Tags": "warning",
                }
            )
