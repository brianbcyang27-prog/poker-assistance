"""macOS Notification System — Send system notifications to the user."""

import subprocess
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Notification:
    """A system notification."""
    title: str
    message: str
    subtitle: Optional[str] = None
    sound: bool = True
    group: Optional[str] = None
    sent_at: datetime = field(default_factory=datetime.now)


class NotificationManager:
    """Send macOS notifications via osascript."""
    
    def __init__(self):
        self.history: list[Notification] = []
        self.max_history = 100
        self._enabled = True
    
    async def send(
        self,
        title: str,
        message: str,
        subtitle: Optional[str] = None,
        sound: bool = True,
        group: Optional[str] = None,
    ) -> bool:
        """Send a notification. Returns True if successful."""
        if not self._enabled:
            return False
        
        try:
            # Build osascript command
            script_parts = [
                'display notification',
                f'"{self._escape(message)}"',
                'with title',
                f'"{self._escape(title)}"',
            ]
            
            if subtitle:
                script_parts.extend(['subtitle', f'"{self._escape(subtitle)}"'])
            
            if sound:
                script_parts.extend(['sound name', '"default"'])
            
            if group:
                script_parts.extend(['with identifier', f'"{self._escape(group)}"'])
            
            script = ' '.join(script_parts)
            
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            
            notification = Notification(
                title=title,
                message=message,
                subtitle=subtitle,
                sound=sound,
                group=group,
            )
            self.history.append(notification)
            
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
            
            return proc.returncode == 0
        
        except Exception as e:
            return False
    
    async def send_alert(self, title: str, message: str) -> bool:
        """Send an alert dialog (blocking)."""
        try:
            script = (
                f'display dialog "{self._escape(message)}" '
                f'with title "{self._escape(title)}" '
                f'buttons {{"OK"}} default button "OK"'
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
    
    async def send_confirm(self, title: str, message: str) -> bool:
        """Send a confirmation dialog. Returns True if user clicks OK."""
        try:
            script = (
                f'display dialog "{self._escape(message)}" '
                f'with title "{self._escape(title)}" '
                f'buttons {{"Cancel", "OK"}} default button "OK"'
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
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    @property
    def is_enabled(self) -> bool:
        return self._enabled
    
    def get_history(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Get recent notification history."""
        return [
            {
                "title": n.title,
                "message": n.message,
                "subtitle": n.subtitle,
                "sound": n.sound,
                "group": n.group,
                "sent_at": n.sent_at.isoformat(),
            }
            for n in self.history[-limit:]
        ]
    
    @staticmethod
    def _escape(text: str) -> str:
        """Escape special characters for osascript."""
        return text.replace("\\", "\\\\").replace('"', '\\"')
