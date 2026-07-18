"""Playwright browser provider.

Wraps Playwright for browser automation:
- Browser launch with profiles
- Navigation
- Element interaction
- Content extraction
- Screenshots
- Cookie management

All methods are async and return structured results.
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

log = logging.getLogger("jarvis.browser.playwright")


@dataclass
class BrowserResult:
    """Result of a Playwright operation."""
    ok: bool = True
    data: dict = None
    error: str = ""

    def __post_init__(self):
        if self.data is None:
            self.data = {}

    def to_dict(self) -> dict:
        return {"ok": self.ok, "data": self.data, "error": self.error}


class PlaywrightProvider:
    """Playwright-based browser automation provider.

    Manages browser lifecycle and provides safe wrappers
    for all browser interactions.

    Usage:
        provider = PlaywrightProvider()
        await provider.start()
        result = await provider.navigate("https://example.com")
        html = await provider.get_content()
        await provider.stop()
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._initialized = False

    async def start(
        self,
        headless: bool = True,
        profile_dir: Optional[str] = None,
    ) -> BrowserResult:
        """Start the browser."""
        if self._initialized:
            return BrowserResult(ok=True, data={"message": "Already running"})

        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()

            launch_args = {
                "headless": headless,
                "args": [
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
            }

            self._browser = await self._playwright.chromium.launch(**launch_args)

            # Create context with optional persistent storage
            context_args = {
                "viewport": {"width": 1280, "height": 720},
                "user_agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
            if profile_dir:
                context_args["storage_state"] = profile_dir

            self._context = await self._browser.new_context(**context_args)
            self._page = await self._context.new_page()
            self._initialized = True

            log.info("Browser started")
            return BrowserResult(ok=True, data={"status": "started"})

        except ImportError:
            return BrowserResult(
                ok=False,
                error="Playwright not installed. Run: pip install playwright && playwright install",
            )
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def stop(self):
        """Stop the browser and clean up."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            log.debug(f"Error stopping browser: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            self._initialized = False
            log.info("Browser stopped")

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> BrowserResult:
        """Navigate to a URL."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            import time
            start = time.time()
            response = await self._page.goto(url, wait_until=wait_until, timeout=30000)
            duration = (time.time() - start) * 1000

            status = response.status if response else 0
            title = await self._page.title()
            current_url = self._page.url

            return BrowserResult(ok=status < 400, data={
                "url": current_url,
                "title": title,
                "status": status,
                "duration_ms": round(duration, 2),
            })

        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def get_content(self) -> BrowserResult:
        """Get the full HTML content of the current page."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            html = await self._page.content()
            title = await self._page.title()
            url = self._page.url
            return BrowserResult(ok=True, data={
                "html": html[:500_000],
                "title": title,
                "url": url,
            })
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def get_text(self) -> BrowserResult:
        """Get the visible text content of the current page."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            text = await self._page.inner_text("body")
            return BrowserResult(ok=True, data={"text": text[:100_000]})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def click(self, selector: str) -> BrowserResult:
        """Click an element by CSS selector."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            await self._page.click(selector, timeout=10000)
            return BrowserResult(ok=True, data={"clicked": selector})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def type_text(self, selector: str, text: str) -> BrowserResult:
        """Type text into an input element."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            await self._page.fill(selector, text, timeout=10000)
            return BrowserResult(ok=True, data={"typed": text[:100], "selector": selector})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def press_key(self, key: str) -> BrowserResult:
        """Press a keyboard key."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            await self._page.keyboard.press(key)
            return BrowserResult(ok=True, data={"key": key})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def scroll(self, direction: str = "down", amount: int = 500) -> BrowserResult:
        """Scroll the page."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            delta = amount if direction == "down" else -amount
            await self._page.mouse.wheel(0, delta)
            return BrowserResult(ok=True, data={"direction": direction, "amount": amount})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def screenshot(self, path: Optional[str] = None) -> BrowserResult:
        """Take a screenshot of the current page."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            import time
            if not path:
                path = f"/tmp/jarvis_browser_{int(time.time())}.png"
            await self._page.screenshot(path=path, full_page=False)
            return BrowserResult(ok=True, data={"path": path})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def wait_for(self, selector: str, timeout: int = 10000) -> BrowserResult:
        """Wait for an element to appear."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return BrowserResult(ok=True, data={"selector": selector})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def evaluate(self, expression: str) -> BrowserResult:
        """Execute JavaScript in the page."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            result = await self._page.evaluate(expression)
            return BrowserResult(ok=True, data={"result": str(result)[:5000]})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def get_cookies(self) -> BrowserResult:
        """Get all cookies."""
        if not self._context:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            cookies = await self._context.cookies()
            return BrowserResult(ok=True, data={"cookies": cookies})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def set_cookies(self, cookies: list[dict]) -> BrowserResult:
        """Set cookies."""
        if not self._context:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            await self._context.add_cookies(cookies)
            return BrowserResult(ok=True, data={"count": len(cookies)})
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    async def search(self, query: str, engine: str = "google") -> BrowserResult:
        """Search using a search engine."""
        urls = {
            "google": f"https://www.google.com/search?q={query}",
            "duckduckgo": f"https://duckduckgo.com/?q={query}",
            "bing": f"https://www.bing.com/search?q={query}",
        }
        url = urls.get(engine, urls["google"])
        return await self.navigate(url)

    async def get_page_info(self) -> BrowserResult:
        """Get current page information."""
        if not self._page:
            return BrowserResult(ok=False, error="Browser not started")

        try:
            title = await self._page.title()
            url = self._page.url
            return BrowserResult(ok=True, data={
                "url": url,
                "title": title,
            })
        except Exception as e:
            return BrowserResult(ok=False, error=str(e))

    @property
    def is_running(self) -> bool:
        return self._initialized

    def get_stats(self) -> dict:
        return {
            "initialized": self._initialized,
            "has_page": self._page is not None,
        }


# Module-level singleton
playwright_provider = PlaywrightProvider()
