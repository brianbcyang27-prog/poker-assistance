"""Linux Accessibility Provider — stub for future implementation.

Uses AT-SPI2 (Assistive Technology Service Provider Interface).
Not implemented yet — raises NotImplementedError.
"""

from typing import Optional

from .base import AccessibilityProvider
from .element import UIElement


class LinuxAccessibilityProvider(AccessibilityProvider):
    """Linux AT-SPI2 provider — not yet implemented.

    Will use:
      - pyatspi2 (GNOME accessibility)
      - or AT-SPI2 D-Bus interface
    """

    async def get_windows(self) -> list[dict]:
        raise NotImplementedError("Linux accessibility provider not yet implemented")

    async def get_active_window(self) -> Optional[dict]:
        raise NotImplementedError("Linux accessibility provider not yet implemented")

    async def get_elements(self, window_title: str = "") -> list[UIElement]:
        raise NotImplementedError("Linux accessibility provider not yet implemented")

    async def find_element(self, name: str = "", role: str = "", app: str = "") -> Optional[UIElement]:
        raise NotImplementedError("Linux accessibility provider not yet implemented")

    async def click_element(self, element: UIElement) -> dict:
        raise NotImplementedError("Linux accessibility provider not yet implemented")

    async def type_text(self, element: UIElement, text: str) -> dict:
        raise NotImplementedError("Linux accessibility provider not yet implemented")

    async def get_tree(self, window_title: str = "") -> dict:
        raise NotImplementedError("Linux accessibility provider not yet implemented")

    async def activate_app(self, app_name: str) -> dict:
        raise NotImplementedError("Linux accessibility provider not yet implemented")
