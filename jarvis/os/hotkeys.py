"""Global Hotkey Management — Register and handle keyboard shortcuts."""

import subprocess
import asyncio
from typing import Optional, Dict, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time


@dataclass
class Hotkey:
    """A registered hotkey."""
    shortcut: str  # e.g., "cmd+shift+j"
    action: str  # Action name to execute
    description: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class HotkeyManager:
    """Register and handle global keyboard shortcuts via macOS APIs."""
    
    def __init__(self):
        self.hotkeys: Dict[str, Hotkey] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._last_keys = set()
    
    def register(
        self,
        shortcut: str,
        action: str,
        description: str = "",
        callback: Optional[Callable] = None,
    ) -> bool:
        """Register a hotkey."""
        hotkey = Hotkey(
            shortcut=shortcut,
            action=action,
            description=description,
        )
        self.hotkeys[action] = hotkey
        
        if callback:
            self._callbacks[action] = callback
        
        return True
    
    def unregister(self, action: str) -> bool:
        """Unregister a hotkey."""
        if action in self.hotkeys:
            del self.hotkeys[action]
            self._callbacks.pop(action, None)
            return True
        return False
    
    def enable(self, action: str) -> bool:
        """Enable a hotkey."""
        if action in self.hotkeys:
            self.hotkeys[action].enabled = True
            return True
        return False
    
    def disable(self, action: str) -> bool:
        """Disable a hotkey."""
        if action in self.hotkeys:
            self.hotkeys[action].enabled = False
            return True
        return False
    
    def start_listening(self):
        """Start listening for hotkeys via osascript."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
        )
        self._monitor_thread.start()
    
    def stop_listening(self):
        """Stop listening for hotkeys."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None
    
    def _listen_loop(self):
        """Background loop to detect key events via screencapture/hotkey."""
        # This is a simplified implementation
        # In production, use pynput or similar library
        while self._monitoring:
            try:
                # Check for modifier keys via ioreg
                proc = subprocess.run(
                    ["ioreg", "-l", "-w", "0"],
                    capture_output=True,
                    timeout=1,
                )
                # Parse modifier key states
                # This is a placeholder - real implementation uses pynput
                pass
            except Exception:
                pass
            
            time.sleep(0.1)
    
    def simulate_shortcut(self, shortcut: str) -> bool:
        """Simulate a keyboard shortcut via osascript."""
        try:
            # Parse shortcut into key combo
            parts = shortcut.lower().split("+")
            modifiers = []
            key = ""
            
            for part in parts:
                if part in ("cmd", "command"):
                    modifiers.append("command down")
                elif part in ("ctrl", "control"):
                    modifiers.append("control down")
                elif part in ("alt", "option", "opt"):
                    modifiers.append("option down")
                elif part in ("shift",):
                    modifiers.append("shift down")
                else:
                    key = part
            
            if not key:
                return False
            
            # Build osascript keystroke
            mod_str = ", ".join(modifiers) if modifiers else ""
            script = (
                f'tell application "System Events" to '
                f'keystroke "{key}" using {{{mod_str}}}'
            )
            
            proc = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5,
            )
            return proc.returncode == 0
        
        except Exception:
            return False
    
    def get_registered(self) -> list:
        """Get all registered hotkeys."""
        return [
            {
                "shortcut": h.shortcut,
                "action": h.action,
                "description": h.description,
                "enabled": h.enabled,
                "created_at": h.created_at.isoformat(),
            }
            for h in self.hotkeys.values()
        ]
    
    @property
    def is_listening(self) -> bool:
        return self._monitoring
