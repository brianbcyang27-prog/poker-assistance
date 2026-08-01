"""Mouse and keyboard control via native macOS commands."""

import asyncio
import shlex

_SUBPROCESS_TIMEOUT = 10  # seconds


async def _run_subprocess(
    cmd: list[str], timeout: float = _SUBPROCESS_TIMEOUT
) -> tuple[bytes, bytes]:
    """Run a subprocess with timeout. Returns (stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout, stderr
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise TimeoutError(f"Command timed out after {timeout}s: {cmd[0]}")


class MouseController:
    """Controls mouse and keyboard using macOS Accessibility."""

    async def move(self, x: int, y: int) -> dict:
        try:
            script = f'tell application "System Events" to set position of mouse to {{{x}, {y}}}'
            await _run_subprocess(["osascript", "-e", script])
            return {"ok": True, "x": x, "y": y}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> dict:
        try:
            if x is not None and y is not None:
                await self.move(x, y)
                await asyncio.sleep(0.1)
            await _run_subprocess(["cliclick", f"c:{x or 0},{y or 0}"])
            return {"ok": True, "x": x, "y": y, "button": button}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def double_click(self, x: int, y: int) -> dict:
        try:
            await _run_subprocess(["cliclick", f"dc:{x},{y}"])
            return {"ok": True, "x": x, "y": y}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def type_text(self, text: str) -> dict:
        """Type text using clipboard paste (works with all characters)."""
        try:
            # Use pbcopy + Cmd+V for reliable typing
            await _run_subprocess(["bash", "-c", f"printf %s {shlex.quote(text)} | pbcopy"])
            await asyncio.sleep(0.05)

            # Paste with Cmd+V
            script = 'tell application "System Events" to keystroke "v" using command down'
            await _run_subprocess(["osascript", "-e", script])
            return {"ok": True, "text": text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def hotkey(self, *keys: str) -> dict:
        """Press a keyboard shortcut (e.g., hotkey('command', 'c'))."""
        try:
            modifiers = []
            key = None
            for k in keys:
                kl = k.lower()
                if kl in ("command", "cmd"):
                    modifiers.append("command down")
                elif kl in ("control", "ctrl"):
                    modifiers.append("control down")
                elif kl in ("option", "alt"):
                    modifiers.append("option down")
                elif kl in ("shift",):
                    modifiers.append("shift down")
                else:
                    key = k

            if not key:
                return {"ok": False, "error": "No key specified"}

            if modifiers:
                mod_str = " & ".join(modifiers)
                script = (
                    f'tell application "System Events" to keystroke "{key}" using {{{mod_str}}}'
                )
            else:
                script = f'tell application "System Events" to keystroke "{key}"'

            _, stderr = await _run_subprocess(["osascript", "-e", script])
            if stderr:
                return {"ok": False, "error": stderr.decode().strip()}
            return {"ok": True, "keys": list(keys)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def press_key(self, key: str) -> dict:
        """Press a special key (return, tab, escape, delete, etc.)."""
        try:
            key_map = {
                "enter": "return",
                "return": "return",
                "tab": "tab",
                "escape": "escape",
                "delete": "delete",
                "backspace": "delete",
                "up": "up arrow",
                "down": "down arrow",
                "left": "left arrow",
                "right": "right arrow",
                "space": "space",
                "home": "home",
                "end": "end",
                "pageup": "page up",
                "pagedown": "page down",
            }
            mapped = key_map.get(key.lower(), key)
            script = f'tell application "System Events" to key code {self._key_code(mapped)}'
            await _run_subprocess(["osascript", "-e", script])
            return {"ok": True, "key": key}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _key_code(self, key: str) -> int:
        codes = {
            "return": 36,
            "tab": 48,
            "escape": 53,
            "delete": 51,
            "space": 49,
            "up arrow": 126,
            "down arrow": 125,
            "left arrow": 123,
            "right arrow": 124,
            "home": 115,
            "end": 119,
            "page up": 116,
            "page down": 121,
        }
        return codes.get(key, 0)

    async def scroll(self, direction: str = "down", amount: int = 5) -> dict:
        try:
            for _ in range(abs(amount)):
                sign = "1" if direction == "down" else "-1"
                await _run_subprocess(["cliclick", f"sc:0,{sign * 3}"])
            return {"ok": True, "direction": direction}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_mouse_position(self) -> dict:
        try:
            script = """
            tell application "System Events"
                set pos to position of mouse
                return item 1 of pos & "," & item 2 of pos
            end tell
            """
            stdout, _ = await _run_subprocess(["osascript", "-e", script])
            pos = stdout.decode().strip().split(",")
            return {"ok": True, "x": int(pos[0]), "y": int(pos[1])}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_screen_size(self) -> dict:
        try:
            script = """
            tell application "Finder"
                set screenBounds to bounds of window of desktop
                return item 3 of screenBounds & "," & item 4 of screenBounds
            end tell
            """
            stdout, _ = await _run_subprocess(["osascript", "-e", script])
            size = stdout.decode().strip().split(",")
            return {"ok": True, "width": int(size[0]), "height": int(size[1])}
        except Exception as e:
            return {"ok": False, "error": str(e)}


mouse = MouseController()
