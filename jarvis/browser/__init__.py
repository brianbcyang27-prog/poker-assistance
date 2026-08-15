"""Browser module — Web browsing capabilities for JARVIS v4.3.0.

Provides secure browser automation through a central BrowserManager.
Workers should NEVER directly control the browser — everything goes through the manager.

Usage:
    from jarvis.browser import browser_manager
    result = await browser_manager.navigate("https://example.com")
    data = await browser_manager.extract()
"""

from .browser_state import BrowserState, BrowserStatus, TabInfo
from .extractor import PageData, PageExtractor, extractor
from .manager import BrowserManager, browser_manager
from .playwright_provider import BrowserResult, PlaywrightProvider, playwright_provider
from .security import BrowserDecision, BrowserSecurity
from .sessions import BrowserSession, SessionManager, session_manager

__all__ = [
    "BrowserState",
    "BrowserStatus",
    "TabInfo",
    "BrowserSecurity",
    "BrowserDecision",
    "SessionManager",
    "BrowserSession",
    "session_manager",
    "PageExtractor",
    "PageData",
    "extractor",
    "PlaywrightProvider",
    "BrowserResult",
    "playwright_provider",
    "BrowserManager",
    "browser_manager",
]
