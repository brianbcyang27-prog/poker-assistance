"""Screen capture and analysis."""
import asyncio
import base64
import subprocess
from pathlib import Path
from typing import Optional

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


class ScreenController:
    """Captures and analyzes the screen."""

    async def capture(self, name: Optional[str] = None) -> dict:
        """Take a screenshot of the entire screen."""
        try:
            fname = name or f"screen_{int(asyncio.get_event_loop().time())}"
            path = SCREENSHOT_DIR / f"{fname}.png"

            proc = await asyncio.create_subprocess_exec(
                "screencapture", "-x", str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            if path.exists():
                return {"ok": True, "path": str(path), "filename": path.name}
            return {"ok": False, "error": "Screenshot failed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def capture_region(self, x: int, y: int, width: int, height: int, name: Optional[str] = None) -> dict:
        """Capture a specific region of the screen."""
        try:
            fname = name or f"region_{int(asyncio.get_event_loop().time())}"
            path = SCREENSHOT_DIR / f"{fname}.png"

            proc = await asyncio.create_subprocess_exec(
                "screencapture", "-x", "-R", f"{x},{y},{width},{height}", str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()

            if path.exists():
                return {"ok": True, "path": str(path), "filename": path.name}
            return {"ok": False, "error": "Region capture failed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_active_window(self) -> dict:
        """Get information about the active window."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set appName to name of frontApp
                set windowTitle to ""
                try
                    set windowTitle to name of front window of frontApp
                end try
                return appName & "|||" & windowTitle
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            parts = stdout.decode().strip().split("|||")
            return {
                "ok": True,
                "app": parts[0] if parts else "",
                "title": parts[1] if len(parts) > 1 else ""
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def open_app(self, app_name: str) -> dict:
        """Open an application."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "open", "-a", app_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            await asyncio.sleep(1)
            return {"ok": True, "app": app_name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def open_url(self, url: str) -> dict:
        """Open a URL in the default browser."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "open", url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return {"ok": True, "url": url}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def list_windows(self) -> dict:
        """List all visible windows."""
        try:
            script = '''
            tell application "System Events"
                set appList to every application process whose visible is true
                set result to ""
                repeat with appProc in appList
                    set appName to name of appProc
                    try
                        set winCount to count of windows of appProc
                        set result to result & appName & " (" & winCount & " windows)" & linefeed
                    end try
                end repeat
                return result
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            windows = [w.strip() for w in stdout.decode().strip().split("\n") if w.strip()]
            return {"ok": True, "windows": windows}
        except Exception as e:
            return {"ok": False, "error": str(e)}


screen = ScreenController()
