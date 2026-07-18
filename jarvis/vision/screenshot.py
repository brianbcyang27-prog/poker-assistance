"""Screenshot capture system.

Provides full screen, application window, and region capture.
Stores screenshots with metadata for vision analysis.
"""

import asyncio
import os
import time
import logging
import base64
from typing import Optional
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.vision.screenshot")

SCREENSHOT_DIR = "/tmp/jarvis_screenshots"


@dataclass
class ScreenRegion:
    """A rectangular region of the screen."""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    def is_valid(self) -> bool:
        return self.width > 0 and self.height > 0


@dataclass
class CapturedScreenshot:
    """A captured screenshot with metadata."""
    id: str = ""
    path: str = ""
    timestamp: float = 0.0
    application: str = ""
    region: Optional[ScreenRegion] = None
    width: int = 0
    height: int = 0
    file_size: int = 0
    base64: str = ""  # cached base64 for provider upload

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "timestamp": self.timestamp,
            "application": application if (application := self.application) else "",
            "region": self.region.to_dict() if self.region else None,
            "width": self.width,
            "height": self.height,
            "file_size": self.file_size,
        }


class ScreenCapture:
    """Screen capture system for JARVIS.

    Captures screenshots using macOS screencapture command.
    Supports full screen, active window, and region capture.
    Caches base64 encoding for efficient provider upload.

    Usage:
        capture = ScreenCapture()
        screenshot = await capture.full_screen()
        screenshot = await capture.active_window()
        screenshot = await capture.region(ScreenRegion(0, 0, 800, 600))
    """

    def __init__(self, capture_dir: str = SCREENSHOT_DIR):
        self._dir = capture_dir
        self._counter = 0
        os.makedirs(self._dir, exist_ok=True)

    def _next_id(self) -> str:
        self._counter += 1
        return f"screenshot_{int(time.time())}_{self._counter:04d}"

    async def _run_screencapture(self, args: list, path: str) -> bool:
        """Run the screencapture command."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "screencapture", *args, path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception as e:
            log.warning("screencapture failed: %s", e)
            return False

    def _get_image_size(self, path: str) -> tuple:
        """Get image dimensions using Python (no PIL dependency — parse PNG header)."""
        try:
            with open(path, "rb") as f:
                header = f.read(32)
            # PNG header: width at bytes 16-19, height at bytes 20-23
            if header[:8] == b'\x89PNG\r\n\x1a\n':
                w = int.from_bytes(header[16:20], 'big')
                h = int.from_bytes(header[20:24], 'big')
                return w, h
        except Exception:
            pass
        return 1920, 1080  # fallback

    async def full_screen(self) -> Optional[CapturedScreenshot]:
        """Capture the entire screen."""
        sid = self._next_id()
        path = os.path.join(self._dir, f"{sid}.png")

        if not await self._run_screencapture(["-x", path], path):
            return None

        w, h = self._get_image_size(path)
        file_size = os.path.getsize(path)

        screenshot = CapturedScreenshot(
            id=sid,
            path=path,
            timestamp=time.time(),
            width=w,
            height=h,
            file_size=file_size,
        )
        log.info("Full screen captured: %s (%dx%d)", sid, w, h)
        return screenshot

    async def active_window(self) -> Optional[CapturedScreenshot]:
        """Capture the active window."""
        sid = self._next_id()
        path = os.path.join(self._dir, f"{sid}.png")

        # -l1 captures the frontmost window
        if not await self._run_screencapture(["-x", "-l1", path], path):
            return None

        w, h = self._get_image_size(path)
        file_size = os.path.getsize(path)

        # Detect which app is active
        app = await self._get_active_app()

        screenshot = CapturedScreenshot(
            id=sid,
            path=path,
            timestamp=time.time(),
            application=app,
            width=w,
            height=h,
            file_size=file_size,
        )
        log.info("Active window captured: %s (%s, %dx%d)", sid, app, w, h)
        return screenshot

    async def region(self, r: ScreenRegion) -> Optional[CapturedScreenshot]:
        """Capture a specific screen region."""
        if not r.is_valid():
            return None

        sid = self._next_id()
        path = os.path.join(self._dir, f"{sid}.png")

        # -R x,y,w,h captures a region
        region_str = f"{r.x},{r.y},{r.width},{r.height}"
        if not await self._run_screencapture(["-x", "-R", region_str, path], path):
            return None

        file_size = os.path.getsize(path)

        screenshot = CapturedScreenshot(
            id=sid,
            path=path,
            timestamp=time.time(),
            region=r,
            width=r.width,
            height=r.height,
            file_size=file_size,
        )
        log.info("Region captured: %s (%s)", sid, region_str)
        return screenshot

    async def _get_active_app(self) -> str:
        """Get the name of the active application."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                return name of frontApp
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            return stdout.decode().strip()
        except Exception:
            return ""

    def get_base64(self, screenshot: CapturedScreenshot) -> str:
        """Get base64-encoded image data from a screenshot."""
        if screenshot.base64:
            return screenshot.base64
        try:
            with open(screenshot.path, "rb") as f:
                data = f.read()
            screenshot.base64 = base64.b64encode(data).decode("utf-8")
            return screenshot.base64
        except Exception as e:
            log.warning("Failed to read screenshot for base64: %s", e)
            return ""

    async def cleanup(self, max_age_seconds: int = 3600):
        """Remove old screenshots."""
        now = time.time()
        count = 0
        for fname in os.listdir(self._dir):
            fpath = os.path.join(self._dir, fname)
            if os.path.isfile(fpath):
                age = now - os.path.getmtime(fpath)
                if age > max_age_seconds:
                    os.remove(fpath)
                    count += 1
        if count:
            log.info("Cleaned up %d old screenshots", count)
