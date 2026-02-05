import asyncio
import random
import os
import logging
from datetime import date, datetime
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Optional, Literal
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

from app.scrapers.extractors import UnifiedExtractor, PriceExtractor

logger = logging.getLogger(__name__)


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
    
    NOTE: Each scrape creates a fresh browser instance to avoid state leakage
    and crashes between scrapes. The overhead is acceptable for 2-6 scrapes/day.
    """
    BASE_URL = "https://www.google.com/travel/flights"
    SCREENSHOTS_DIR = Path("/app/data/screenshots")
    HTML_SNAPSHOTS_DIR = Path("/app/data/html_snapshots")
    
    # Browser launch arguments for headless operation
    BROWSER_ARGS = [
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
    
    # Price selectors - multiple fallbacks for resilience against layout changes
    PRICE_SELECTORS = [
        "[data-gs]",                           # Primary: data-gs attribute
        "span[aria-label*='dollars']",         # Fallback: aria-label with price
        "span[aria-label*='NZD']",             # Fallback: NZD currency
        ".YMlIz",                              # Fallback: price class (may change)
        "[jsname='IWWDBc']",                   # Fallback: jsname for price element
        "div[class*='price'] span",           # Generic price div
    ]
    
    def __init__(self, screenshots_dir: Optional[Path] = None, html_dir: Optional[Path] = None):
        self.screenshots_dir = screenshots_dir or self.SCREENSHOTS_DIR
        self.html_dir = html_dir or self.HTML_SNAPSHOTS_DIR
        
        # Ensure directories exist
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.html_dir.mkdir(parents=True, exist_ok=True)
        
        # Store playwright instance for cleanup (set during scrape)
        self._playwright = None
        self._browser = None
    
    def _build_url(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date],
        adults: int = 2,
        children: int = 2,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        cabin_class: str = "economy",
        stops_filter: str = "any",
        currency: str = "NZD",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
    ) -> str:
        """Delegate to centralized URL builder."""
        from app.utils.template_helpers import build_google_flights_url
        return build_google_flights_url(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            adults=adults,
            children=children,
            infants_in_seat=infants_in_seat,
            infants_on_lap=infants_on_lap,
            cabin_class=cabin_class,
            stops_filter=stops_filter,
            currency=currency,
            carry_on_bags=carry_on_bags,
            checked_bags=checked_bags,
        )
    
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
        children: int = 2,
        infants_in_seat: int = 0,
        infants_on_lap: int = 0,
        cabin_class: str = "economy",
        stops_filter: str = "any",
        currency: str = "NZD",
        carry_on_bags: int = 0,
        checked_bags: int = 0,
    ) -> ScrapeResult:
        """
        Scrape Google Flights with proper failure classification.
        
        Creates a fresh browser instance for each scrape to avoid state leakage
        and crashes between scrapes (fixes cascading browser context failures).
        
        Returns ScrapeResult with:
        - status: success/captcha/timeout/layout_change/no_results/blocked/network_error/unknown
        - prices: List of FlightResult (empty on failure)
        - screenshot_path/html_snapshot_path: Paths to artifacts on failure
        - error_message: Human-readable error description
        """
        start_time = datetime.utcnow()
        
        # Create fresh playwright and browser for this scrape
        # This avoids browser crashes affecting subsequent scrapes
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=self.BROWSER_ARGS
        )
        
        context = await self._browser.new_context(
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
            url = self._build_url(
                origin, destination, departure_date, return_date,
                adults=adults, children=children,
                infants_in_seat=infants_in_seat, infants_on_lap=infants_on_lap,
                cabin_class=cabin_class, stops_filter=stops_filter,
                currency=currency, carry_on_bags=carry_on_bags,
                checked_bags=checked_bags,
            )
            
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
            
            # Wait for page to have content - try primary selectors first
            page_ready = False
            for selector in self.PRICE_SELECTORS[:3]:  # Try top 3 selectors
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    page_ready = True
                    break
                except PlaywrightTimeout:
                    continue

            if not page_ready:
                # Check if it's a no-results page vs layout change
                no_flights_indicators = [
                    "no flights found",
                    "no matching flights",
                    "try different dates",
                    "we couldn't find",
                ]
                content = (await page.content()).lower()

                if any(indicator in content for indicator in no_flights_indicators):
                    return ScrapeResult(
                        status="no_results",
                        error_message="No flights found for this route/date combination",
                        duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    )

            # Use the unified extractor with 20+ fallback strategies
            logger.info(f"Starting extraction for {origin}->{destination}")
            flights = await UnifiedExtractor.extract_all(page)

            if not flights:
                # No flights extracted - try to determine why
                screenshot_path, html_path = await self._save_failure_artifacts(
                    page, search_definition_id, "layout_change"
                )
                return ScrapeResult(
                    status="layout_change",
                    error_message="No prices extracted using 20+ fallback strategies - Google may have changed page structure",
                    screenshot_path=screenshot_path,
                    html_snapshot_path=html_path,
                    duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
                )

            # Convert extracted flights to FlightResult objects
            for flight in flights:
                results.append(FlightResult(
                    price_nzd=Decimal(flight.price),
                    airline=flight.airline or "Unknown",
                    stops=flight.stops if flight.stops is not None else 0,
                    duration_minutes=flight.duration_minutes or 0,
                    departure_time="",
                    arrival_time="",
                    raw_data={
                        "price_confidence": flight.price_confidence,
                        "price_strategy": flight.price_strategy,
                        "airline_confidence": flight.airline_confidence,
                        "airline_strategy": flight.airline_strategy,
                        "stops_confidence": flight.stops_confidence,
                        "duration_confidence": flight.duration_confidence,
                        "overall_confidence": flight.overall_confidence,
                        "extraction_summary": flight.extraction_summary,
                    }
                ))

            logger.info(
                f"Extracted {len(results)} flights for {origin}->{destination}. "
                f"Best price: ${results[0].price_nzd if results else 'N/A'}"
            )
            
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
            # Always close context, browser, and playwright to avoid resource leaks
            try:
                await context.close()
            except Exception:
                pass
            
            await self._cleanup_browser()
    
    async def _cleanup_browser(self):
        """Clean up browser and playwright instances."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
    
    async def close(self):
        """Clean up resources. Called for backward compatibility."""
        await self._cleanup_browser()


class ScraperError(Exception):
    """Legacy exception - prefer using ScrapeResult.status for error handling."""
    pass
