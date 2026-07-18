"""AccessibilityManager — JARVIS's semantic eyes.

Central manager that:
  - Loads the platform-specific accessibility provider
  - Provides high-level semantic actions
  - Maintains current UI state
  - Integrates with ComputerManager for permission gating

Usage:
    from jarvis.computer.accessibility import accessibility_manager
    tree = await accessibility_manager.get_tree()
    element = tree.find("Save button")
    await accessibility_manager.click("Save button")
"""

import asyncio
import logging
import sys
import time
from typing import Optional

from .element import UIElement
from .tree import AccessibilityTree

log = logging.getLogger("jarvis.computer.accessibility.manager")


class AccessibilityManager:
    """Central accessibility management — JARVIS's eyes.

    Provides semantic UI interaction:
      - get_tree() — full UI element tree
      - find(query) — find element by natural language
      - click(query) — click on element by name
      - type_into(query, text) — type into field by name
      - activate(app) — bring app to foreground

    Loads the appropriate platform provider at initialization.
    """

    def __init__(self):
        self._provider = None
        self._platform = ""
        self._initialized = False
        self._last_tree: Optional[AccessibilityTree] = None
        self._last_tree_time: float = 0

    async def initialize(self) -> dict:
        """Load the platform-specific accessibility provider."""
        if self._initialized:
            return {"ok": True, "platform": self._platform}

        platform = sys.platform

        if platform == "darwin":
            from .macos import MacOSAccessibilityProvider
            self._provider = MacOSAccessibilityProvider()
            self._platform = "macos"
        elif platform == "win32":
            from .windows import WindowsAccessibilityProvider
            self._provider = WindowsAccessibilityProvider()
            self._platform = "windows"
        else:
            from .linux import LinuxAccessibilityProvider
            self._provider = LinuxAccessibilityProvider()
            self._platform = "linux"

        self._initialized = True
        log.info("Accessibility provider loaded: %s", self._platform)
        return {"ok": True, "platform": self._platform}

    async def shutdown(self):
        """Cleanup."""
        self._provider = None
        self._initialized = False
        self._last_tree = None

    def _check(self):
        """Ensure provider is loaded."""
        if not self._initialized or not self._provider:
            raise RuntimeError("AccessibilityManager not initialized — call initialize() first")

    async def get_windows(self) -> list[dict]:
        """Get all visible windows."""
        self._check()
        return await self._provider.get_windows()

    async def get_active_window(self) -> Optional[dict]:
        """Get the currently focused window."""
        self._check()
        return await self._provider.get_active_window()

    async def get_tree(self, window_title: str = "", force: bool = False) -> AccessibilityTree:
        """Get the accessibility tree for a window.

        Caches results for 2 seconds to avoid hammering the API.
        Set force=True to bypass cache.
        """
        self._check()

        now = time.time()
        if not force and self._last_tree and (now - self._last_tree_time) < 2.0:
            return self._last_tree

        elements = await self._provider.get_elements(window_title)
        active = await self._provider.get_active_window()
        app = active["app"] if active else ""
        win = window_title or (active["title"] if active else "")

        tree = AccessibilityTree(elements, app=app, window=win)
        self._last_tree = tree
        self._last_tree_time = now
        return tree

    async def find(self, query: str, app: str = "") -> Optional[UIElement]:
        """Find a UI element by natural language query.

        Examples:
            await accessibility_manager.find("Save")
            await accessibility_manager.find("Export PDF")
            await accessibility_manager.find("search box")
        """
        self._check()
        tree = await self.get_tree()
        return tree.find(query)

    async def find_all(self, query: str) -> list[UIElement]:
        """Find all UI elements matching a query."""
        self._check()
        tree = await self.get_tree()
        return tree.find_all(query)

    async def click(self, query: str, app: str = "") -> dict:
        """Click on a UI element by natural language query.

        Finds the element, then clicks it via accessibility API.

        Returns:
            {"ok": True, "element": "Save", "type": "button", "x": 100, "y": 200}
            or {"ok": False, "error": "No element found matching 'Save'"}
        """
        self._check()
        element = await self.find(query, app=app)
        if not element:
            return {"ok": False, "error": f"No element found matching '{query}'"}

        result = await self._provider.click_element(element)
        result["element"] = element.name
        result["type"] = element.type
        result["role"] = element.role
        return result

    async def type_into(self, query: str, text: str, app: str = "") -> dict:
        """Type text into a UI element found by natural language query.

        Finds the text field/area, focuses it, then types.

        Returns:
            {"ok": True, "element": "Search", "text": "hello"}
            or {"ok": False, "error": "No text field found matching 'Search'"}
        """
        self._check()
        element = await self.find(query, app=app)
        if not element:
            return {"ok": False, "error": f"No element found matching '{query}'"}

        if not element.is_typeable():
            return {"ok": False, "error": f"Element '{element.name}' is not a text field (type={element.type})"}

        result = await self._provider.type_text(element, text)
        result["element"] = element.name
        return result

    async def activate(self, app_name: str) -> dict:
        """Bring an application to the foreground."""
        self._check()
        return await self._provider.activate_app(app_name)

    async def list_apps(self) -> list[str]:
        """Get list of running application names."""
        self._check()
        if hasattr(self._provider, 'get_applications'):
            return await self._provider.get_applications()
        windows = await self._provider.get_windows()
        apps = list({w["app"] for w in windows})
        apps.sort()
        return apps

    async def get_summary(self, window_title: str = "") -> str:
        """Get a compact LLM-ready summary of the current UI state."""
        tree = await self.get_tree(window_title)
        return tree.to_context()

    async def get_stats(self) -> dict:
        """Get current UI element statistics."""
        tree = await self.get_tree()
        return tree.stats()


# Global singleton
accessibility_manager = AccessibilityManager()
