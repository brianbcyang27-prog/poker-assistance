"""Browser Manager — Central gateway for all browser interaction.

Every browser action goes through this manager:
  Agent → BrowserManager → Security Check → Playwright → Extraction → Memory

Workers should NEVER directly call Playwright.
Everything goes through BrowserManager.

Usage:
    from jarvis.browser import browser_manager
    result = await browser_manager.navigate("https://example.com")
    data = await browser_manager.extract()
    print(data.to_llm_context())
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass

from .browser_state import BrowserState, BrowserStatus, TabInfo
from .security import BrowserSecurity, BrowserDecision
from .sessions import SessionManager, session_manager
from .playwright_provider import PlaywrightProvider, playwright_provider, BrowserResult
from .extractor import PageExtractor, PageData, extractor

log = logging.getLogger("jarvis.browser.manager")


class BrowserManager:
    """Central gateway for all browser interaction.

    All browser actions must go through this manager.
    Workers should NEVER directly control the browser.

    Flow:
        1. Agent requests browser action
        2. Manager checks security
        3. If approved, delegates to Playwright
        4. Extracts structured data
        5. Stores in memory
        6. Returns result
    """

    def __init__(self):
        self.state = BrowserState()
        self.security = BrowserSecurity()
        self.sessions = session_manager
        self.provider = playwright_provider
        self.extractor = extractor
        self._action_log: list[dict] = []
        self._initialized = False

    async def initialize(self, headless: bool = True, session_name: Optional[str] = None) -> BrowserResult:
        """Initialize the browser.

        Args:
            headless: Run in headless mode
            session_name: Optional session to restore
        """
        if self._initialized:
            return BrowserResult(ok=True, data={"message": "Already initialized"})

        # Restore session if specified
        profile_dir = None
        if session_name:
            session = await self.sessions.restore(session_name)
            if session:
                profile_dir = session.profile_dir

        result = await self.provider.start(headless=headless, profile_dir=profile_dir)
        if result.ok:
            self._initialized = True
            self.state.update_status(BrowserStatus.IDLE)
            log.info("BrowserManager initialized")

        return result

    async def shutdown(self):
        """Shutdown the browser."""
        # Save cookies from active session
        if self._initialized:
            try:
                cookies_result = await self.provider.get_cookies()
                if cookies_result.ok:
                    # Save to default session
                    await self.sessions.save_cookies("default", cookies_result.data.get("cookies", []))
            except Exception:
                pass

        await self.provider.stop()
        self._initialized = False
        self.state.update_status(BrowserStatus.CLOSED)
        log.info("BrowserManager shut down")

    async def execute(
        self,
        action: str,
        agent: str = "",
        task_id: str = "",
        **params,
    ) -> dict:
        """Execute a browser action through the security pipeline.

        Args:
            action: Action name (navigate, click, type, extract, etc.)
            agent: Which worker is requesting
            task_id: Associated task ID
            **params: Action-specific parameters

        Returns:
            dict with ok, data, risk_level, duration_ms
        """
        start = time.time()

        # Security check
        url = params.get("url", self.state.current_url)
        decision = self.security.check_action(action, url=url, agent=agent)

        if not decision.allowed:
            self._log_action(action, "denied", agent, decision.risk_level)
            return {
                "ok": False,
                "error": decision.reason,
                "risk_level": decision.risk_level,
                "requires_approval": decision.requires_approval,
            }

        # Validate action exists before trying to init browser
        handler = self._get_handler(action)
        if not handler:
            return {"ok": False, "error": f"Unknown action: {action}"}

        # Ensure browser is running
        if not self._initialized:
            init_result = await self.initialize()
            if not init_result.ok:
                return {"ok": False, "error": f"Browser init failed: {init_result.error}"}

        try:
            result = await handler(**params)
            duration = (time.time() - start) * 1000

            # Log success
            self._log_action(action, "success", agent, decision.risk_level, duration_ms=duration)

            # Emit event
            await self._emit_event(action, result, agent, decision.risk_level)

            result["risk_level"] = decision.risk_level
            result["duration_ms"] = round(duration, 2)
            return result

        except Exception as e:
            duration = (time.time() - start) * 1000
            self.state.set_error(str(e))
            self._log_action(action, "failed", agent, decision.risk_level, error=str(e))
            return {"ok": False, "error": str(e), "duration_ms": round(duration, 2)}

    def _get_handler(self, action: str):
        """Get handler for an action."""
        handlers = {
            "navigate": self._navigate,
            "search": self._search,
            "click": self._click,
            "type": self._type,
            "scroll": self._scroll,
            "press_key": self._press_key,
            "extract": self._extract,
            "extract_text": self._extract_text,
            "screenshot": self._screenshot,
            "get_content": self._get_content,
            "get_text": self._get_text,
            "back": self._back,
            "forward": self._forward,
            "reload": self._reload,
            "new_tab": self._new_tab,
            "close_tab": self._close_tab,
            "wait_for": self._wait_for,
            "evaluate": self._evaluate,
            "get_page_info": self._get_page_info,
            "get_cookies": self._get_cookies,
        }
        return handlers.get(action)

    # ── Action Handlers ──────────────────────────────────────

    async def _navigate(self, url: str = "", wait_until: str = "domcontentloaded", **kw) -> dict:
        """Navigate to a URL."""
        self.state.update_status(BrowserStatus.NAVIGATING, f"navigate:{url}")
        result = await self.provider.navigate(url, wait_until=wait_until)
        if result.ok:
            data = result.data
            self.state.update_navigation(
                url=data.get("url", url),
                title=data.get("title", ""),
                duration_ms=data.get("duration_ms", 0),
            )
        else:
            self.state.set_error(result.error)
        return result.to_dict()

    async def _search(self, query: str = "", engine: str = "google", **kw) -> dict:
        """Search using a search engine."""
        self.state.update_status(BrowserStatus.NAVIGATING, f"search:{query}")
        result = await self.provider.search(query, engine)
        if result.ok:
            data = result.data
            self.state.update_navigation(
                url=data.get("url", ""),
                title=data.get("title", ""),
                duration_ms=data.get("duration_ms", 0),
            )
        return result.to_dict()

    async def _click(self, selector: str = "", **kw) -> dict:
        """Click an element."""
        self.state.update_status(BrowserStatus.BROWSING, f"click:{selector}")
        result = await self.provider.click(selector)
        return result.to_dict()

    async def _type(self, selector: str = "", text: str = "", **kw) -> dict:
        """Type into an element."""
        self.state.update_status(BrowserStatus.FILLING_FORM, f"type:{selector}")
        result = await self.provider.type_text(selector, text)
        return result.to_dict()

    async def _scroll(self, direction: str = "down", amount: int = 500, **kw) -> dict:
        """Scroll the page."""
        result = await self.provider.scroll(direction, amount)
        return result.to_dict()

    async def _press_key(self, key: str = "", **kw) -> dict:
        """Press a key."""
        result = await self.provider.press_key(key)
        return result.to_dict()

    async def _extract(self, **kw) -> dict:
        """Extract structured data from the current page."""
        self.state.update_status(BrowserStatus.EXTRACTING)
        content_result = await self.provider.get_content()
        if not content_result.ok:
            return content_result.to_dict()

        html = content_result.data.get("html", "")
        url = content_result.data.get("url", self.state.current_url)
        page_data = await self.extractor.extract_from_html(html, url=url)

        # Update state
        self.state.current_title = page_data.title

        return {
            "ok": True,
            "data": page_data.to_dict(),
            "context": page_data.to_llm_context(),
        }

    async def _extract_text(self, **kw) -> dict:
        """Extract just the text content."""
        result = await self.provider.get_text()
        return result.to_dict()

    async def _screenshot(self, path: str = None, **kw) -> dict:
        """Take a screenshot."""
        result = await self.provider.screenshot(path)
        return result.to_dict()

    async def _get_content(self, **kw) -> dict:
        """Get raw HTML content."""
        result = await self.provider.get_content()
        return result.to_dict()

    async def _get_text(self, **kw) -> dict:
        """Get visible text content."""
        result = await self.provider.get_text()
        return result.to_dict()

    async def _back(self, **kw) -> dict:
        """Go back in history."""
        if self.provider._page:
            await self.provider._page.go_back()
            info = await self.provider.get_page_info()
            if info.ok:
                self.state.current_url = info.data.get("url", "")
                self.state.current_title = info.data.get("title", "")
            return {"ok": True}
        return {"ok": False, "error": "No page"}

    async def _forward(self, **kw) -> dict:
        """Go forward in history."""
        if self.provider._page:
            await self.provider._page.go_forward()
            info = await self.provider.get_page_info()
            if info.ok:
                self.state.current_url = info.data.get("url", "")
                self.state.current_title = info.data.get("title", "")
            return {"ok": True}
        return {"ok": False, "error": "No page"}

    async def _reload(self, **kw) -> dict:
        """Reload the current page."""
        if self.provider._page:
            await self.provider._page.reload()
            return {"ok": True}
        return {"ok": False, "error": "No page"}

    async def _new_tab(self, url: str = "", **kw) -> dict:
        """Open a new tab."""
        if self.provider._context:
            page = await self.provider._context.new_page()
            if url:
                await page.goto(url)
            return {"ok": True, "url": url}
        return {"ok": False, "error": "No context"}

    async def _close_tab(self, **kw) -> dict:
        """Close the current tab."""
        if self.provider._page:
            await self.provider._page.close()
            self.provider._page = None
            return {"ok": True}
        return {"ok": False, "error": "No page"}

    async def _wait_for(self, selector: str = "", timeout: int = 10000, **kw) -> dict:
        """Wait for an element."""
        result = await self.provider.wait_for(selector, timeout)
        return result.to_dict()

    async def _evaluate(self, expression: str = "", **kw) -> dict:
        """Execute JavaScript."""
        result = await self.provider.evaluate(expression)
        return result.to_dict()

    async def _get_page_info(self, **kw) -> dict:
        """Get current page info."""
        result = await self.provider.get_page_info()
        return result.to_dict()

    async def _get_cookies(self, **kw) -> dict:
        """Get cookies."""
        result = await self.provider.get_cookies()
        return result.to_dict()

    # ── Helpers ──────────────────────────────────────────────

    def _log_action(self, action: str, status: str, agent: str, risk_level: str, **kw):
        """Log an action."""
        entry = {
            "action": action,
            "status": status,
            "agent": agent,
            "risk_level": risk_level,
            "timestamp": time.time(),
            **kw,
        }
        self._action_log.append(entry)
        if len(self._action_log) > 500:
            self._action_log = self._action_log[-250:]

    async def _emit_event(self, action: str, result: dict, agent: str, risk_level: str):
        """Emit a browser action event."""
        try:
            from ..core.events import event_bus, Event
            status = "completed" if result.get("ok") else "failed"
            await event_bus.emit(Event(
                type=f"browser.action.{status}",
                data={
                    "action": action,
                    "status": status,
                    "risk_level": risk_level,
                    "agent": agent,
                    "url": self.state.current_url,
                },
                source=agent or "browser",
            ))
        except Exception:
            pass

    def get_actions(self) -> list[str]:
        """List available browser actions."""
        return [
            "navigate", "search", "click", "type", "scroll", "press_key",
            "extract", "extract_text", "screenshot", "get_content", "get_text",
            "back", "forward", "reload", "new_tab", "close_tab",
            "wait_for", "evaluate", "get_page_info", "get_cookies",
        ]

    def get_recent_actions(self, limit: int = 20) -> list[dict]:
        return self._action_log[-limit:]

    def get_state(self) -> dict:
        return self.state.to_dict()

    def get_stats(self) -> dict:
        return {
            "initialized": self._initialized,
            "actions_logged": len(self._action_log),
            "state": self.state.status,
            "current_url": self.state.current_url,
            "security": self.security.get_stats(),
            "sessions": self.sessions.get_stats(),
            "provider": self.provider.get_stats(),
        }


# Module-level singleton
browser_manager = BrowserManager()
