"""OS Manager — Unified interface for system-level control."""

import asyncio
from typing import Optional, Dict, Any, List
from .notifications import NotificationManager
from .clipboard import ClipboardManager
from .hotkeys import HotkeyManager
from .menubar import MenuBarManager
from .watcher import FileWatcher


class OSManager:
    """Unified interface for JARVIS OS integration."""
    
    def __init__(self):
        self.notifications = NotificationManager()
        self.clipboard = ClipboardManager()
        self.hotkeys = HotkeyManager()
        self.menubar = MenuBarManager()
        self.watcher = FileWatcher()
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the OS integration layer."""
        if self._initialized:
            return True
        
        # Start clipboard monitoring
        self.clipboard.start_monitoring(interval=1.0)
        
        self._initialized = True
        return True
    
    async def shutdown(self):
        """Shutdown the OS integration layer."""
        self.clipboard.stop_monitoring()
        self.hotkeys.stop_listening()
        self.watcher.stop_monitoring()
        self._initialized = False
    
    # ---- Notifications ----
    
    async def notify(
        self,
        title: str,
        message: str,
        subtitle: Optional[str] = None,
        sound: bool = True,
    ) -> bool:
        """Send a system notification."""
        return await self.notifications.send(title, message, subtitle, sound)
    
    async def alert(self, title: str, message: str) -> bool:
        """Show an alert dialog."""
        return await self.notifications.send_alert(title, message)
    
    async def confirm(self, title: str, message: str) -> bool:
        """Show a confirmation dialog."""
        return await self.notifications.send_confirm(title, message)
    
    # ---- Clipboard ----
    
    async def clipboard_read(self) -> Optional[str]:
        """Read the clipboard."""
        return await self.clipboard.get_content()
    
    async def clipboard_write(self, text: str) -> bool:
        """Write to the clipboard."""
        return await self.clipboard.set_content(text)
    
    async def clipboard_clear(self) -> bool:
        """Clear the clipboard."""
        return await self.clipboard.clear()
    
    async def clipboard_has_image(self) -> bool:
        """Check if clipboard contains an image."""
        return await self.clipboard.get_image() is not None
    
    def clipboard_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get clipboard history."""
        return self.clipboard.get_history(limit)
    
    # ---- Hotkeys ----
    
    def hotkey_register(
        self,
        shortcut: str,
        action: str,
        description: str = "",
    ) -> bool:
        """Register a global hotkey."""
        return self.hotkeys.register(shortcut, action, description)
    
    def hotkey_unregister(self, action: str) -> bool:
        """Unregister a hotkey."""
        return self.hotkeys.unregister(action)
    
    def hotkey_list(self) -> List[Dict[str, Any]]:
        """List registered hotkeys."""
        return self.hotkeys.get_registered()
    
    def hotkey_simulate(self, shortcut: str) -> bool:
        """Simulate a keyboard shortcut."""
        return self.hotkeys.simulate_shortcut(shortcut)
    
    # ---- Menu Bar ----
    
    async def menubar_add(self, key: str, title: str, tooltip: Optional[str] = None) -> bool:
        """Add a menu bar item."""
        return await self.menubar.add_item(key, title, tooltip=tooltip)
    
    async def menubar_update(self, key: str, title: str, tooltip: Optional[str] = None) -> bool:
        """Update a menu bar item."""
        return await self.menubar.update_item(key, title, tooltip)
    
    async def menubar_remove(self, key: str) -> bool:
        """Remove a menu bar item."""
        return await self.menubar.remove_item(key)
    
    def menubar_list(self) -> List[Dict[str, Any]]:
        """List menu bar items."""
        return self.menubar.get_items()
    
    # ---- File Watcher ----
    
    async def watch_directory(
        self,
        path: str,
        key: Optional[str] = None,
        recursive: bool = True,
    ) -> bool:
        """Start watching a directory."""
        return await self.watcher.watch(path, key, recursive)
    
    async def unwatch_directory(self, key: str) -> bool:
        """Stop watching a directory."""
        return await self.watcher.unwatch(key)
    
    def watched_directories(self) -> List[Dict[str, Any]]:
        """List watched directories."""
        return self.watcher.get_watched()
    
    def file_events(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent file events."""
        return self.watcher.get_events(limit)
    
    # ---- System Info ----
    
    async def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        import platform
        import os
        
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "user": os.getenv("USER", "unknown"),
            "home": os.path.expanduser("~"),
            "cwd": os.getcwd(),
            "pid": os.getpid(),
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get OS integration status."""
        return {
            "initialized": self._initialized,
            "notifications_enabled": self.notifications.is_enabled,
            "clipboard_monitoring": self.clipboard.is_monitoring,
            "clipboard_history_size": len(self.clipboard.history),
            "hotkeys_listening": self.hotkeys.is_listening,
            "hotkeys_registered": len(self.hotkeys.hotkeys),
            "menubar_items": len(self.menubar.items),
            "watcher_monitoring": self.watcher.is_monitoring,
            "watched_directories": len(self.watcher.watchers),
            "file_events": len(self.watcher.events),
        }
