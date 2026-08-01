"""Menu Bar Manager — Display status items in the macOS menu bar."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MenuBarItem:
    """A menu bar status item."""

    title: str
    icon: str | None = None
    tooltip: str | None = None
    items: list[dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class MenuBarManager:
    """Display status items in the macOS menu bar via JXA (JavaScript for Automation)."""

    def __init__(self):
        self.items: dict[str, MenuBarItem] = {}
        self._active = False

    async def add_item(
        self,
        key: str,
        title: str,
        icon: str | None = None,
        tooltip: str | None = None,
    ) -> bool:
        """Add a status item to the menu bar."""
        item = MenuBarItem(
            title=title,
            icon=icon,
            tooltip=tooltip,
        )
        self.items[key] = item
        return True

    async def update_item(self, key: str, title: str, tooltip: str | None = None) -> bool:
        """Update a menu bar item."""
        if key in self.items:
            self.items[key].title = title
            if tooltip is not None:
                self.items[key].tooltip = tooltip
            return True
        return False

    async def remove_item(self, key: str) -> bool:
        """Remove a menu bar item."""
        if key in self.items:
            del self.items[key]
            return True
        return False

    async def set_menu(self, key: str, items: list[dict[str, str]]) -> bool:
        """Set dropdown menu items for a status item."""
        if key in self.items:
            self.items[key].items = items
            return True
        return False

    def get_items(self) -> list[dict[str, Any]]:
        """Get all menu bar items."""
        return [
            {
                "key": k,
                "title": v.title,
                "icon": v.icon,
                "tooltip": v.tooltip,
                "items": v.items,
            }
            for k, v in self.items.items()
        ]

    async def show_notification_indicator(self, count: int) -> bool:
        """Show a notification badge count in the menu bar."""
        if count > 0:
            await self.add_item("notifications", f"🔔 {count}", tooltip=f"{count} notifications")
        else:
            await self.remove_item("notifications")
        return True
