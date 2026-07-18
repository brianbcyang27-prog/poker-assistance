"""Abstract accessibility provider interface.

Each platform (macOS, Windows, Linux) implements this interface
so JARVIS can inspect UI elements cross-platform.
"""

from abc import ABC, abstractmethod
from typing import Optional
from .element import UIElement


class AccessibilityProvider(ABC):
    """Abstract interface for accessibility inspection.

    Platform providers implement this to expose:
      - Window listing and inspection
      - UI element traversal
      - Element interaction (click, type)
      - Application detection
    """

    @abstractmethod
    async def get_windows(self) -> list[dict]:
        """Get all visible windows.

        Returns list of dicts with:
          - app: str (application name)
          - title: str (window title)
          - pid: int (process ID)
          - focused: bool
        """
        pass

    @abstractmethod
    async def get_active_window(self) -> Optional[dict]:
        """Get the currently focused window.

        Returns dict with:
          - app: str
          - title: str
          - pid: int
        """
        pass

    @abstractmethod
    async def get_elements(self, window_title: str = "") -> list[UIElement]:
        """Get UI elements from a window.

        Args:
            window_title: Specific window to inspect.
                         Empty = active window.

        Returns list of UIElement objects.
        """
        pass

    @abstractmethod
    async def find_element(
        self,
        name: str = "",
        role: str = "",
        app: str = "",
    ) -> Optional[UIElement]:
        """Find a specific UI element by name and/or role.

        Args:
            name: Element name/label to match
            role: Element type/role to match
            app: Restrict to specific application

        Returns first matching UIElement or None.
        """
        pass

    @abstractmethod
    async def click_element(self, element: UIElement) -> dict:
        """Click on a UI element.

        Uses element bounds to calculate click position.
        Falls back to accessibility action if bounds unavailable.

        Returns {"ok": bool, ...}
        """
        pass

    @abstractmethod
    async def type_text(self, element: UIElement, text: str) -> dict:
        """Type text into a UI element.

        Focuses the element first, then types the text.

        Returns {"ok": bool, ...}
        """
        pass

    @abstractmethod
    async def get_tree(self, window_title: str = "") -> dict:
        """Get the full accessibility tree for a window.

        Returns nested dict representing the element hierarchy.
        """
        pass

    @abstractmethod
    async def activate_app(self, app_name: str) -> dict:
        """Bring an application to the foreground.

        Returns {"ok": bool, ...}
        """
        pass
