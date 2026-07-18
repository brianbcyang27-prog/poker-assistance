"""Clipboard Management — Read, write, and monitor the system clipboard."""

import subprocess
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time


@dataclass
class ClipboardEntry:
    """A clipboard entry."""
    content: str
    content_type: str  # text, image, file
    copied_at: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None  # app that copied it


class ClipboardManager:
    """Read, write, and monitor the macOS clipboard."""
    
    def __init__(self):
        self.history: List[ClipboardEntry] = []
        self.max_history = 50
        self._last_content = ""
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: List = []
    
    async def get_content(self) -> Optional[str]:
        """Read current clipboard content (text only)."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pbpaste",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                content = stdout.decode("utf-8", errors="replace")
                return content if content else None
            return None
        except Exception:
            return None
    
    async def set_content(self, text: str) -> bool:
        """Write text to the clipboard."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pbcopy",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=text.encode("utf-8"))
            
            if proc.returncode == 0:
                entry = ClipboardEntry(
                    content=text[:1000],  # Truncate for history
                    content_type="text",
                    source="jarvis",
                )
                self.history.append(entry)
                if len(self.history) > self.max_history:
                    self.history = self.history[-self.max_history:]
                return True
            return False
        except Exception:
            return False
    
    async def clear(self) -> bool:
        """Clear the clipboard."""
        return await self.set_content("")
    
    async def get_image(self) -> Optional[str]:
        """Check if clipboard contains an image (returns file path or None)."""
        try:
            script = (
                'tell application "System Events" to '
                'if (clipboard info) contains "TIFF picture" then return "image" '
                'else if (clipboard info) contains "PNGf" then return "image" '
                'else return "text"'
            )
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            result = stdout.decode("utf-8", errors="replace").strip()
            return "image" if result == "image" else None
        except Exception:
            return None
    
    async def paste_to_active_app(self, text: str) -> bool:
        """Type text directly into the active application (bypass clipboard)."""
        try:
            # Use osascript to keystroke the text
            script = (
                f'tell application "System Events" to '
                f'keystroke "{text.replace(chr(34), chr(34)+chr(34))}"'
            )
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False
    
    def start_monitoring(self, interval: float = 1.0):
        """Start monitoring clipboard changes in background."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(interval,),
            daemon=True,
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring clipboard changes."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
            self._monitor_thread = None
    
    def on_change(self, callback):
        """Register a callback for clipboard changes."""
        self._callbacks.append(callback)
    
    def _monitor_loop(self, interval: float):
        """Background loop to detect clipboard changes."""
        while self._monitoring:
            try:
                proc = subprocess.run(
                    ["pbpaste"],
                    capture_output=True,
                    timeout=1,
                )
                content = proc.stdout.decode("utf-8", errors="replace")
                
                if content and content != self._last_content:
                    self._last_content = content
                    entry = ClipboardEntry(
                        content=content[:1000],
                        content_type="text",
                    )
                    self.history.append(entry)
                    if len(self.history) > self.max_history:
                        self.history = self.history[-self.max_history:]
                    
                    for cb in self._callbacks:
                        try:
                            cb(entry)
                        except Exception:
                            pass
            except Exception:
                pass
            
            time.sleep(interval)
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent clipboard history."""
        return [
            {
                "content": e.content[:200],  # Truncate for display
                "content_type": e.content_type,
                "copied_at": e.copied_at.isoformat(),
                "source": e.source,
            }
            for e in self.history[-limit:]
        ]
    
    @property
    def is_monitoring(self) -> bool:
        return self._monitoring
