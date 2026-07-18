"""Menu Bar Manager — Display status items in the macOS menu bar."""

import subprocess
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MenuBarItem:
    """A menu bar status item."""
    title: str
    icon: Optional[str] = None
    tooltip: Optional[str] = None
    items: List[Dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class MenuBarManager:
    """Display status items in the macOS menu bar via JXA (JavaScript for Automation)."""
    
    def __init__(self):
        self.items: Dict[str, MenuBarItem] = {}
        self._active = False
    
    async def add_item(
        self,
        key: str,
        title: str,
        icon: Optional[str] = None,
        tooltip: Optional[str] = None,
    ) -> bool:
        """Add a status item to the menu bar."""
        item = MenuBarItem(
            title=title,
            icon=icon,
            tooltip=tooltip,
        )
        self.items[key] = item
        return True
    
    async def update_item(self, key: str, title: str, tooltip: Optional[str] = None) -> bool:
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
    
    async def set_menu(self, key: str, items: List[Dict[str, str]]) -> bool:
        """Set dropdown menu items for a status item."""
        if key in self.items:
            self.items[key].items = items
            return True
        return False
    
    def get_items(self) -> List[Dict[str, Any]]:
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
