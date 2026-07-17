"""Browser automation via Playwright."""
import asyncio
import base64
import os
from pathlib import Path
from typing import Optional

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


class BrowserController:
    """Controls a Chromium browser instance."""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self._context = None

    async def start(self, headless: bool = True):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        self._context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        self.page = await self._context.new_page()
        return True

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.browser = None
        self.page = None
        self.playwright = None

    async def navigate(self, url: str) -> dict:
        if not self.page:
            await self.start()
        try:
            resp = await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            title = await self.page.title()
            return {
                "ok": True,
                "url": self.page.url,
                "title": title,
                "status": resp.status if resp else None
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def screenshot(self, name: Optional[str] = None) -> dict:
        if not self.page:
            return {"ok": False, "error": "No page open"}
        try:
            fname = name or f"screen_{int(asyncio.get_event_loop().time())}"
            path = SCREENSHOT_DIR / f"{fname}.png"
            await self.page.screenshot(path=str(path), full_page=False)
            return {"ok": True, "path": str(path), "filename": path.name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_text(self) -> dict:
        if not self.page:
            return {"ok": False, "error": "No page open"}
        try:
            text = await self.page.inner_text("body")
            title = await self.page.title()
            return {"ok": True, "text": text[:8000], "title": title, "url": self.page.url}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def click(self, selector: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No page open"}
        try:
            await self.page.click(selector, timeout=10000)
            await asyncio.sleep(0.5)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def type_text(self, selector: str, text: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No page open"}
        try:
            await self.page.fill(selector, text, timeout=10000)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def press_key(self, key: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No page open"}
        try:
            await self.page.keyboard.press(key)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def evaluate(self, expression: str) -> dict:
        if not self.page:
            return {"ok": False, "error": "No page open"}
        try:
            result = await self.page.evaluate(expression)
            return {"ok": True, "result": str(result)[:4000]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def scroll(self, direction: str = "down", amount: int = 500) -> dict:
        if not self.page:
            return {"ok": False, "error": "No page open"}
        try:
            delta = amount if direction == "down" else -amount
            await self.page.mouse.wheel(0, delta)
            await asyncio.sleep(0.3)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def search_google(self, query: str) -> dict:
        if not self.page:
            await self.start()
        try:
            await self.page.goto(
                f"https://www.google.com/search?q={query}",
                wait_until="domcontentloaded",
                timeout=15000
            )
            await asyncio.sleep(1)
            results = await self.page.evaluate("""
                () => {
                    const items = document.querySelectorAll('div.g');
                    return Array.from(items).slice(0, 8).map(item => {
                        const link = item.querySelector('a');
                        const title = item.querySelector('h3');
                        const snippet = item.querySelector('[data-sncf], .VwiC3b');
                        return {
                            title: title ? title.textContent : '',
                            url: link ? link.href : '',
                            snippet: snippet ? snippet.textContent : ''
                        };
                    });
                }
            """)
            return {"ok": True, "results": results, "query": query}
        except Exception as e:
            return {"ok": False, "error": str(e)}


browser = BrowserController()
