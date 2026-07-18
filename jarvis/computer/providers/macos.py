"""macOS platform provider.

Implements computer control using macOS-native tools:
- AppleScript for UI automation
- screencapture for screenshots
- osascript for shell integration
- NSWorkspace for app management
"""

import os
import asyncio
import logging
from typing import Optional

log = logging.getLogger("jarvis.computer.providers.macos")


class MacOSProvider:
    """macOS-native computer control provider.

    All methods are async and return dicts with {"ok": bool, ...}.
    """

    async def screenshot(self, path: Optional[str] = None) -> dict:
        """Take a screenshot of the entire screen."""
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
            if proc.returncode == 0 and os.path.exists(path):
                return {"ok": True, "path": path}
            return {"ok": False, "error": "screencapture failed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def open_app(self, app_name: str) -> dict:
        """Open a macOS application."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "open", "-a", app_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return {"ok": proc.returncode == 0, "app": app_name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def close_app(self, app_name: str) -> dict:
        """Close a macOS application gracefully."""
        try:
            script = f'tell application "{app_name}" to quit'
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return {"ok": proc.returncode == 0, "app": app_name}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_active_window(self) -> dict:
        """Get the currently focused window info."""
        try:
            script = '''
            tell application "System Events"
                set frontApp to first application process whose frontmost is true
                set appName to name of frontApp
                try
                    set winTitle to name of first window of frontApp
                on error
                    set winTitle to ""
                end try
                return appName & "|||" & winTitle
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
                app, title = result.split("|||", 1)
                return {"ok": True, "app": app, "title": title}
            return {"ok": False, "error": "Could not parse window info"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def list_windows(self) -> dict:
        """List all visible windows."""
        try:
            script = '''
            tell application "System Events"
                set winList to ""
                repeat with proc in (every application process whose visible is true)
                    set procName to name of proc
                    repeat with win in (every window of proc)
                        set winTitle to name of win
                        set winList to winList & procName & "|||" & winTitle & "\\n"
                    end repeat
                end repeat
                return winList
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode().strip()
            windows = []
            for line in output.split("\n"):
                if "|||" in line:
                    app, title = line.split("|||", 1)
                    windows.append({"app": app.strip(), "title": title.strip()})
            return {"ok": True, "windows": windows}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def click(self, x: int, y: int, button: str = "left") -> dict:
        """Click at coordinates using cliclick (if installed) or osascript."""
        try:
            if button == "right":
                # Right click via osascript
                script = f'''
                tell application "System Events"
                    click at {{{x}, {y}}} using button 2
                end tell
                '''
                proc = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return {"ok": proc.returncode == 0, "x": x, "y": y, "button": button}

            # Left click via cliclick if available, else osascript
            proc = await asyncio.create_subprocess_exec(
                "which", "cliclick",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if proc.returncode == 0:
                proc = await asyncio.create_subprocess_exec(
                    "cliclick", f"c:{x},{y}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return {"ok": proc.returncode == 0, "x": x, "y": y}
            else:
                script = f'''
                tell application "System Events"
                    click at {{{x}, {y}}}
                end tell
                '''
                proc = await asyncio.create_subprocess_exec(
                    "osascript", "-e", script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                return {"ok": proc.returncode == 0, "x": x, "y": y}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def type_text(self, text: str) -> dict:
        """Type text using AppleScript."""
        try:
            # Escape for AppleScript
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')
            script = f'''
            tell application "System Events"
                keystroke "{escaped}"
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return {"ok": proc.returncode == 0, "text": text[:100]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def press_key(self, key: str) -> dict:
        """Press a single key."""
        try:
            script = f'''
            tell application "System Events"
                key code {self._key_code(key)}
            end tell
            '''
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return {"ok": proc.returncode == 0, "key": key}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def hotkey(self, *keys: str) -> dict:
        """Press a keyboard shortcut (e.g., cmd+c)."""
        try:
            if not keys:
                return {"ok": False, "error": "No keys specified"}

            # Build modifier + key script
            modifiers = []
            main_key = keys[-1]
            for k in keys[:-1]:
                mod = self._modifier_name(k)
                if mod:
                    modifiers.append(mod)

            if modifiers:
                mod_str = " ".join(modifiers)
                script = f'''
                tell application "System Events"
                    keystroke "{main_key}" using {{{mod_str}}}
                end tell
                '''
            else:
                script = f'''
                tell application "System Events"
                    keystroke "{main_key}"
                end tell
                '''

            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            return {"ok": proc.returncode == 0, "keys": list(keys)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _key_code(self, key: str) -> int:
        """Map key name to macOS key code."""
        codes = {
            "return": 36, "enter": 36, "tab": 48, "space": 49,
            "delete": 51, "backspace": 51, "escape": 53, "esc": 53,
            "left": 123, "right": 124, "down": 125, "up": 126,
            "f1": 122, "f2": 120, "f3": 99, "f4": 118,
            "f5": 96, "f6": 97, "f7": 98, "f8": 100,
            "f9": 101, "f10": 109, "f11": 103, "f12": 111,
        }
        return codes.get(key.lower(), ord(key.lower()) if len(key) == 1 else 0)

    def _modifier_name(self, key: str) -> str:
        """Map key name to AppleScript modifier."""
        modifiers = {
            "command": "command down", "cmd": "command down",
            "shift": "shift down", "alt": "option down",
            "option": "option down", "ctrl": "control down",
            "control": "control down",
        }
        return modifiers.get(key.lower(), "")

    async def get_screen_size(self) -> dict:
        """Get screen resolution."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "osascript", "-e",
                'tell application "Finder" to get bounds of window of desktop',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            parts = [int(x.strip()) for x in stdout.decode().strip().split(",")]
            if len(parts) == 4:
                return {"ok": True, "width": parts[2] - parts[0], "height": parts[3] - parts[1]}
        except Exception:
            pass
        return {"ok": True, "width": 1920, "height": 1080}
