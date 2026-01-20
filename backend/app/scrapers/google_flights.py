import asyncio
import random
from datetime import date
from decimal import Decimal
from dataclasses import dataclass
from typing import List, Optional
from playwright.async_api import async_playwright, Page, Browser


@dataclass
class FlightResult:
    price_nzd: Decimal
    airline: str
    stops: int
    duration_minutes: int
    departure_time: str
    arrival_time: str
    raw_data: dict


class GoogleFlightsScraper:
    BASE_URL = "https://www.google.com/travel/flights"
    
    def __init__(self):
        self.browser: Optional[Browser] = None
    
    async def _get_browser(self) -> Browser:
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
        return self.browser
    
    def _build_url(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: date,
        passengers: int = 4
    ) -> str:
        dep_str = departure_date.strftime("%Y-%m-%d")
        ret_str = return_date.strftime("%Y-%m-%d")
        
        return (
            f"{self.BASE_URL}?q=flights%20from%20{origin}%20to%20{destination}"
            f"%20on%20{dep_str}%20return%20{ret_str}"
            f"&curr=NZD&hl=en"
        )
    
    async def _random_delay(self, min_sec: float = 2.0, max_sec: float = 5.0):
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def scrape_route(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: date,
        passengers: int = 4
    ) -> List[FlightResult]:
        browser = await self._get_browser()
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-NZ",
            timezone_id="Pacific/Auckland",
        )
        
        page = await context.new_page()
        results: List[FlightResult] = []
        
        try:
            url = self._build_url(origin, destination, departure_date, return_date, passengers)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await self._random_delay(3, 6)
            
            await page.wait_for_selector("[data-gs]", timeout=15000)
            
            price_elements = await page.query_selector_all("[data-gs]")
            
            for element in price_elements[:10]:
                try:
                    price_text = await element.inner_text()
                    price_clean = price_text.replace("$", "").replace(",", "").replace("NZD", "").strip()
                    
                    if price_clean.isdigit():
                        results.append(FlightResult(
                            price_nzd=Decimal(price_clean),
                            airline="Unknown",
                            stops=0,
                            duration_minutes=0,
                            departure_time="",
                            arrival_time="",
                            raw_data={"price_text": price_text}
                        ))
                except Exception:
                    continue
            
        except Exception as e:
            raise ScraperError(f"Failed to scrape Google Flights: {str(e)}")
        
        finally:
            await context.close()
        
        return results
    
    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None


class ScraperError(Exception):
    pass
