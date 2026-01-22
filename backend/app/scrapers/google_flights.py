import asyncio
import random
import os
from datetime import date, datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Optional, Literal
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout


# Failure reason classification
FailureReason = Literal[
    "success",
    "captcha",
    "timeout",
    "layout_change",
    "no_results",
    "blocked",
    "network_error",
    "unknown"
]


@dataclass
class FlightResult:
    """A single flight option from scraping."""
    price_nzd: Decimal
    airline: str
    stops: int
    duration_minutes: int
    departure_time: str
    arrival_time: str
    raw_data: dict


@dataclass
class ScrapeResult:
    """
    Complete result of a scrape attempt with failure classification.
    
    Oracle Review: "Missing first-class scrape health model with failure reason classification."
    """
    status: FailureReason
    prices: List[FlightResult] = field(default_factory=list)
    screenshot_path: Optional[str] = None
    html_snapshot_path: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: int = 0
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_success(self) -> bool:
        return self.status == "success"
    
    @property
    def has_prices(self) -> bool:
        return len(self.prices) > 0


class GoogleFlightsScraper:
    """
    Google Flights scraper with proper failure handling and circuit breaker support.
    
    Key features (from Oracle review):
    - Failure reason classification
    - Screenshot + HTML capture on failure
    - Circuit breaker integration
    - Proper timeout handling
    """
    BASE_URL = "https://www.google.com/travel/flights"
    SCREENSHOTS_DIR = Path("/app/data/screenshots")
    HTML_SNAPSHOTS_DIR = Path("/app/data/html_snapshots")
    
    # Captcha detection patterns
    CAPTCHA_SELECTORS = [
        "iframe[src*='recaptcha']",
        "#captcha",
        ".g-recaptcha",
        "[data-callback='onCaptcha']",
    ]
    
    # Blocked/rate-limited detection
    BLOCKED_PATTERNS = [
        "unusual traffic",
        "automated requests",
        "verify you're not a robot",
        "access denied",
    ]
    
    def __init__(self, screenshots_dir: Optional[Path] = None, html_dir: Optional[Path] = None):
        self.browser: Optional[Browser] = None
        self.screenshots_dir = screenshots_dir or self.SCREENSHOTS_DIR
        self.html_dir = html_dir or self.HTML_SNAPSHOTS_DIR
        
        # Ensure directories exist
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.html_dir.mkdir(parents=True, exist_ok=True)
    
    async def _get_browser(self) -> Browser:
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--disable-extensions",
                    "--single-process",
                    "--no-zygote",
                    "--disable-setuid-sandbox",
                    "--disable-accelerated-2d-canvas",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--disable-translate",
                    "--mute-audio",
                    "--hide-scrollbars",
                    "--metrics-recording-only",
                ]
            )
        return self.browser
    
    def _build_url(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int = 2,
        children: int = 2
    ) -> str:
        dep_str = departure_date.strftime("%Y-%m-%d")
        
        url = (
            f"{self.BASE_URL}?q=flights%20from%20{origin}%20to%20{destination}"
            f"%20on%20{dep_str}"
        )
        
        if return_date:
            ret_str = return_date.strftime("%Y-%m-%d")
            url += f"%20return%20{ret_str}"
        
        url += f"&curr=NZD&hl=en"
        
        # Add passenger counts if non-default
        # Google Flights URL params: adults, children, infants
        # Default is 1 adult, so we only add if different
        
        return url
    
    async def _random_delay(self, min_sec: float = 2.0, max_sec: float = 5.0):
        await asyncio.sleep(random.uniform(min_sec, max_sec))
    
    async def _detect_captcha(self, page: Page) -> bool:
        """Check if page shows a captcha."""
        for selector in self.CAPTCHA_SELECTORS:
            try:
                element = await page.query_selector(selector)
                if element:
                    return True
            except Exception:
                continue
        return False
    
    async def _detect_blocked(self, page: Page) -> bool:
        """Check if we're rate-limited or blocked."""
        try:
            content = await page.content()
            content_lower = content.lower()
            return any(pattern in content_lower for pattern in self.BLOCKED_PATTERNS)
        except Exception:
            return False
    
    async def _save_failure_artifacts(
        self,
        page: Page,
        search_def_id: int,
        reason: str
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Save screenshot and HTML snapshot on failure for debugging.
        
        Returns: (screenshot_path, html_path)
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        prefix = f"{search_def_id}_{timestamp}_{reason}"
        
        screenshot_path: Optional[str] = None
        html_path: Optional[str] = None
        
        try:
            screenshot_file = self.screenshots_dir / f"{prefix}.png"
            await page.screenshot(path=str(screenshot_file), full_page=True)
            screenshot_path = str(screenshot_file)
        except Exception as e:
            pass  # Don't fail on screenshot failure
        
        try:
            html_file = self.html_dir / f"{prefix}.html"
            content = await page.content()
            html_file.write_text(content, encoding="utf-8")
            html_path = str(html_file)
        except Exception as e:
            pass  # Don't fail on HTML save failure
        
        return screenshot_path, html_path
    
    async def scrape_route(
        self,
        search_definition_id: int,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int = 2,
        children: int = 2
    ) -> ScrapeResult:
        """
        Scrape Google Flights with proper failure classification.
        
        Returns ScrapeResult with:
        - status: success/captcha/timeout/layout_change/no_results/blocked/network_error/unknown
        - prices: List of FlightResult (empty on failure)
        - screenshot_path/html_snapshot_path: Paths to artifacts on failure
        - error_message: Human-readable error description
        """
        start_time = datetime.utcnow()
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
            url = self._build_url(origin, destination, departure_date, return_date, adults, children)
            
            # Navigate with timeout
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except PlaywrightTimeout:
                screenshot_path, html_path = await self._save_failure_artifacts(
                    page, search_definition_id, "timeout"
                )
                return ScrapeResult(
                    status="timeout",
                    error_message="Page load timed out after 30 seconds",
                    screenshot_path=screenshot_path,
                    html_snapshot_path=html_path,
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            
            await self._random_delay(3, 6)
            
            # Check for captcha
            if await self._detect_captcha(page):
                screenshot_path, html_path = await self._save_failure_artifacts(
                    page, search_definition_id, "captcha"
                )
                return ScrapeResult(
                    status="captcha",
                    error_message="Captcha detected - manual intervention may be required",
                    screenshot_path=screenshot_path,
                    html_snapshot_path=html_path,
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            
            # Check for blocked/rate-limited
            if await self._detect_blocked(page):
                screenshot_path, html_path = await self._save_failure_artifacts(
                    page, search_definition_id, "blocked"
                )
                return ScrapeResult(
                    status="blocked",
                    error_message="Detected rate limiting or block from Google",
                    screenshot_path=screenshot_path,
                    html_snapshot_path=html_path,
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            
            # Wait for flight results to load
            try:
                await page.wait_for_selector("[data-gs]", timeout=15000)
            except PlaywrightTimeout:
                # Check if this is "no results" vs layout change
                no_flights_indicators = [
                    "no flights found",
                    "no matching flights",
                    "try different dates",
                ]
                content = (await page.content()).lower()
                
                if any(indicator in content for indicator in no_flights_indicators):
                    return ScrapeResult(
                        status="no_results",
                        error_message="No flights found for this route/date combination",
                        duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    )
                else:
                    # Likely a layout change if selector not found
                    screenshot_path, html_path = await self._save_failure_artifacts(
                        page, search_definition_id, "layout_change"
                    )
                    return ScrapeResult(
                        status="layout_change",
                        error_message="Expected price elements not found - Google may have changed page structure",
                        screenshot_path=screenshot_path,
                        html_snapshot_path=html_path,
                        duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    )
            
            # Parse price elements
            price_elements = await page.query_selector_all("[data-gs]")
            
            for element in price_elements[:10]:  # Limit to top 10 results
                try:
                    price_text = await element.inner_text()
                    price_clean = price_text.replace("$", "").replace(",", "").replace("NZD", "").strip()
                    
                    if price_clean.isdigit():
                        results.append(FlightResult(
                            price_nzd=Decimal(price_clean),
                            airline="Unknown",  # TODO: Extract airline
                            stops=0,            # TODO: Extract stops
                            duration_minutes=0, # TODO: Extract duration
                            departure_time="",
                            arrival_time="",
                            raw_data={"price_text": price_text}
                        ))
                except Exception:
                    continue
            
            if not results:
                screenshot_path, html_path = await self._save_failure_artifacts(
                    page, search_definition_id, "no_results"
                )
                return ScrapeResult(
                    status="no_results",
                    error_message="Price elements found but could not parse any valid prices",
                    screenshot_path=screenshot_path,
                    html_snapshot_path=html_path,
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )
            
            # Success!
            return ScrapeResult(
                status="success",
                prices=results,
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            
        except Exception as e:
            # Catch-all for unexpected errors
            screenshot_path, html_path = await self._save_failure_artifacts(
                page, search_definition_id, "unknown"
            )
            return ScrapeResult(
                status="unknown",
                error_message=f"Unexpected error: {str(e)}",
                screenshot_path=screenshot_path,
                html_snapshot_path=html_path,
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
        
        finally:
            await context.close()
    
    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None


class ScraperError(Exception):
    """Legacy exception - prefer using ScrapeResult.status for error handling."""
    pass
