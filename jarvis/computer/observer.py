"""Screen observer — inspects current screen state.

Provides capabilities to understand what's on screen:
- Active window detection
- UI element inspection (accessibility tree)
- Screen capture for vision models
- Window listing and management
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

log = logging.getLogger("jarvis.computer.observer")


@dataclass
class WindowInfo:
    """Information about a window."""
    name: str = ""
    app: str = ""
    title: str = ""
    pid: int = 0
    is_focused: bool = False
    bounds: dict = None  # {x, y, width, height}

    def __post_init__(self):
        if self.bounds is None:
            self.bounds = {}

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "app": self.app,
            "title": self.title,
            "pid": self.pid,
            "is_focused": self.is_focused,
            "bounds": self.bounds,
        }


@dataclass
class ScreenState:
    """Current state of the screen."""
    active_window: Optional[WindowInfo] = None
    windows: list[WindowInfo] = None
    screen_size: dict = None  # {width, height}
    screenshot_path: Optional[str] = None

    def __post_init__(self):
        if self.windows is None:
            self.windows = []
        if self.screen_size is None:
            self.screen_size = {"width": 0, "height": 0}

    def to_dict(self) -> dict:
        return {
            "active_window": self.active_window.to_dict() if self.active_window else None,
            "window_count": len(self.windows),
            "windows": [w.to_dict() for w in self.windows[:10]],
            "screen_size": self.screen_size,
            "screenshot_path": self.screenshot_path,
        }


class ScreenObserver:
    """Observes and inspects the current screen state.

    Uses macOS Accessibility APIs and AppleScript for inspection.
    Falls back to screenshot + vision model for understanding.

    Usage:
        observer = ScreenObserver()
        state = await observer.get_state()
        print(state.active_window.app)
    """

    async def get_state(self, capture_screenshot: bool = False) -> ScreenState:
        """Get current screen state."""
        active = await self.get_active_window()
        windows = await self.list_windows()
        size = await self.get_screen_size()

        screenshot_path = None
        if capture_screenshot:
            screenshot_path = await self.take_screenshot()

        return ScreenState(
            active_window=active,
            windows=windows,
            screen_size=size,
            screenshot_path=screenshot_path,
        )

    async def get_active_window(self) -> Optional[WindowInfo]:
        """Get information about the currently focused window."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set appName to name of frontApp
                set appPID to unix id of frontApp
                try
                    set windowTitle to name of first window of frontApp
                on error
                    set windowTitle to ""
                end try
                return appName & "|||" & windowTitle & "|||" & appPID
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            result = stdout.decode().strip()

            if "|||" in result:
                parts = result.split("|||")
                return WindowInfo(
                    app=parts[0],
                    title=parts[1] if len(parts) > 1 else "",
                    pid=int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
                    is_focused=True,
                )
        except Exception as e:
            log.debug(f"Active window detection failed: {e}")
        return None

    async def list_windows(self) -> list[WindowInfo]:
        """List all visible windows."""
        windows = []
        try:
            script = '''
            tell application "System Events"
                set allWindows to {}
                repeat with proc in (every application process whose visible is true)
                    set procName to name of proc
                    repeat with win in (every window of proc)
                        set winTitle to name of win
                        set end of allWindows to procName & "|||" & winTitle
                    end repeat
                end repeat
                return allWindows
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode().strip()

            for line in output.split(", "):
                if "|||" in line:
                    parts = line.split("|||")
                    windows.append(WindowInfo(
                        app=parts[0].strip(),
                        title=parts[1].strip() if len(parts) > 1 else "",
                    ))
        except Exception as e:
            log.debug(f"Window listing failed: {e}")
        return windows

    async def get_screen_size(self) -> dict:
        """Get screen resolution."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e",
                "tell application \"Finder\" to get bounds of window of desktop",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            result = stdout.decode().strip()
            # Format: "x, y, width, height"
            parts = [int(x.strip()) for x in result.split(",")]
            if len(parts) == 4:
                return {"width": parts[2] - parts[0], "height": parts[3] - parts[1]}
        except Exception as e:
            log.debug(f"Screen size detection failed: {e}")
        return {"width": 1920, "height": 1080}

    async def take_screenshot(self, path: Optional[str] = None) -> Optional[str]:
        """Take a screenshot and return the file path."""
        import time
        if path is None:
            path = f"/tmp/jarvis_screenshot_{int(time.time())}.png"
        try:
            proc = await asyncio.create_subprocess_exec(
                "screencapture", "-x", path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode == 0:
                return path
        except Exception as e:
            log.debug(f"Screenshot failed: {e}")
        return None

    async def get_ui_elements(self) -> list[dict]:
        """Get UI elements from the active window via accessibility API."""
        elements = []
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                tell frontApp
                    set uiElements to every UI element of first window
                    set output to ""
                    repeat with elem in uiElements
                        try
                            set elemDesc to description of elem
                            set elemRole to role of elem
                            set elemValue to value of elem
                            set output to output & elemRole & "|||" & elemDesc & "|||" & elemValue & "\\n"
                        end try
                    end repeat
                    return output
                end tell
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode().strip()

            for line in output.split("\n"):
                if "|||" in line:
                    parts = line.split("|||")
                    elements.append({
                        "role": parts[0].strip() if len(parts) > 0 else "",
                        "description": parts[1].strip() if len(parts) > 1 else "",
                        "value": parts[2].strip() if len(parts) > 2 else "",
                    })
        except Exception as e:
            log.debug(f"UI element detection failed: {e}")
        return elements


# Module-level singleton
observer = ScreenObserver()
