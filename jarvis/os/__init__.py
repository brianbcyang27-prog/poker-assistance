"""JARVIS OS Integration — System-level control and awareness."""

from typing import Optional
from .notifications import NotificationManager
from .clipboard import ClipboardManager
from .hotkeys import HotkeyManager
from .menubar import MenuBarManager
from .watcher import FileWatcher
from .manager import OSManager

# Singleton
_os_manager: Optional["OSManager"] = None

def get_os_manager() -> "OSManager":
    global _os_manager
    if _os_manager is None:
        _os_manager = OSManager()
    return _os_manager

__all__ = [
    "NotificationManager",
    "ClipboardManager",
    "HotkeyManager",
    "MenuBarManager",
    "FileWatcher",
    "OSManager",
    "get_os_manager",
]
