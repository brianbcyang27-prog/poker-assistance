"""OS Manager — Unified interface for system-level control."""

import asyncio
import os
import platform
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

import aiofiles
import aiofiles.os

from .clipboard import ClipboardManager
from .hotkeys import HotkeyManager
from .menubar import MenuBarManager
from .notifications import NotificationManager
from .watcher import FileWatcher


class OSManager:
    """Unified interface for JARVIS OS integration."""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.notifications = NotificationManager()
        self.clipboard = ClipboardManager()
        self.hotkeys = HotkeyManager()
        self.menubar = MenuBarManager()
        self.watcher = FileWatcher()
        self._initialized = False

    def _resolve(self, path: str) -> Path:
        """Resolve path relative to base_path."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base_path / p
        return p.resolve()

    async def initialize(self) -> bool:
        """Initialize the OS integration layer."""
        if self._initialized:
            return True

        # Start clipboard monitoring
        self.clipboard.start_monitoring(interval=1.0)

        self._initialized = True
        return True

    async def get_system_info(self) -> dict[str, Any]:
        """Return a lightweight snapshot of the current host."""
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "pid": os.getpid(),
            "cwd": str(self.base_path),
            "initialized": self._initialized,
            "timestamp": time.time(),
        }

    def get_status(self) -> dict[str, Any]:
        """Return the current OS manager state."""
        return {
            "initialized": self._initialized,
            "notifications_enabled": self.notifications.is_enabled,
            "clipboard_monitoring": self.clipboard.is_monitoring,
            "hotkeys_registered": len(self.hotkeys.hotkeys),
            "menu_items": len(self.menubar.items),
            "watchers": len(self.watcher.watchers),
        }

    def hotkey_register(self, shortcut: str, action: str, description: str = "") -> bool:
        """Compatibility wrapper for registering hotkeys."""
        return self.hotkeys.register(shortcut, action, description)

    def hotkey_unregister(self, action: str) -> bool:
        """Compatibility wrapper for unregistering hotkeys."""
        return self.hotkeys.unregister(action)

    def hotkey_list(self) -> list[dict[str, Any]]:
        """Compatibility wrapper for listing registered hotkeys."""
        return self.hotkeys.get_registered()

    def menubar_list(self) -> list[dict[str, Any]]:
        """Compatibility wrapper for listing menu bar items."""
        return self.menubar.get_items()

    def watched_directories(self) -> list[dict[str, Any]]:
        """Compatibility wrapper for watched directories."""
        return self.watcher.get_watched()

    def file_events(self) -> list[dict[str, Any]]:
        """Compatibility wrapper for file watcher events."""
        return self.watcher.get_events()

    async def shutdown(self):
        """Shutdown the OS integration layer."""
        self.clipboard.stop_monitoring()
        self.hotkeys.stop_listening()
        self.watcher.stop_monitoring()
        self._initialized = False

    # ---- File Operations ----

    async def read_file(self, path: str) -> str:
        """Read file contents."""
        p = self._resolve(path)
        if not await aiofiles.os.path.exists(p):
            raise FileNotFoundError(f"File not found: {path}")
        if not await aiofiles.os.path.isfile(p):
            raise ValueError(f"Not a file: {path}")
        async with aiofiles.open(p, encoding="utf-8") as f:
            return await f.read()

    async def write_file(self, path: str, content: str) -> None:
        """Write content to a file (creates parent dirs)."""
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(p, "w", encoding="utf-8") as f:
            await f.write(content)

    async def edit_file(self, path: str, old: str, new: str) -> bool:
        """Replace text in file. Returns True if replacement made."""
        p = self._resolve(path)
        content = await self.read_file(path)
        if old not in content:
            return False
        new_content = content.replace(old, new)
        async with aiofiles.open(p, "w", encoding="utf-8") as f:
            await f.write(new_content)
        return True

    async def create_directory(self, path: str) -> None:
        """Create directory."""
        p = self._resolve(path)
        p.mkdir(parents=True, exist_ok=True)

    async def list_files(
        self, path: str = ".", pattern: str = "*", recursive: bool = False
    ) -> list[dict[str, Any]]:
        """List files matching pattern."""
        p = self._resolve(path)
        if not p.exists():
            return []

        files = []
        if recursive:
            for f in p.rglob(pattern):
                if f.is_file():
                    files.append(self._file_info(f))
        else:
            for f in p.glob(pattern):
                if f.is_file():
                    files.append(self._file_info(f))
        return files

    async def glob(self, pattern: str, path: str = ".") -> list[str]:
        """Find files matching glob pattern."""
        p = self._resolve(path)
        matches = []
        for f in p.rglob(pattern):
            if f.is_file():
                matches.append(str(f.relative_to(self.base_path)))
        return matches

    async def delete(self, path: str, recursive: bool = False) -> bool:
        """Delete file or directory."""
        p = self._resolve(path)
        if not await aiofiles.os.path.exists(p):
            return False
        try:
            if p.is_dir():
                import shutil

                shutil.rmtree(p)
            else:
                await aiofiles.os.remove(p)
            return True
        except Exception:
            return False

    async def copy(self, src: str, dst: str, recursive: bool = False) -> bool:
        """Copy file or directory."""
        src_p = self._resolve(src)
        dst_p = self._resolve(dst)
        if not src_p.exists():
            return False
        try:
            if src_p.is_dir():
                shutil.copytree(src_p, dst_p, dirs_exist_ok=True)
            else:
                dst_p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_p, dst_p)
            return True
        except Exception:
            return False

    async def run_python(self, code: str) -> dict[str, Any]:
        """Run Python code in a subprocess."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=self.base_path
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "python3",
                temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.base_path),
            )
            stdout, stderr = await proc.communicate()
            return {
                "returncode": proc.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
            }
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    async def execute(self, command: str) -> dict[str, Any]:
        """Execute a shell command."""
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(self.base_path),
        )
        stdout, stderr = await proc.communicate()
        return {
            "returncode": proc.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
        }

    def _resolve(self, path: str) -> Path:
        """Resolve path relative to base_path."""
        p = Path(path)
        if not p.is_absolute():
            p = self.base_path / p
        return p.resolve()

    def _file_info(self, f: Path) -> dict[str, Any]:
        stat = f.stat()
        return {
            "path": str(f.relative_to(self.base_path)),
            "absolute": str(f),
            "name": f.name,
            "is_file": f.is_file(),
            "is_dir": f.is_dir(),
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }

    # ---- Notifications ----

    async def notify(
        self,
        title: str,
        message: str,
        subtitle: str | None = None,
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

    async def clipboard_read(self) -> str | None:
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

    def clipboard_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get clipboard history."""
        return self.clipboard.get_history(limit)

    # ---- Vision stubs ----
    async def screenshot(self) -> str:
        """Take a screenshot. Returns path."""
        import tempfile

        path = tempfile.mktemp(suffix=".png")
        return path

    async def get_screen_text(self) -> str:
        """Get text from screen via OCR."""
        return ""

    # ---- Computer control stubs ----
    async def click(self, x: int, y: int, button: str = "left") -> bool:
        return True

    async def type_text(self, text: str) -> bool:
        return True

    async def hotkey(self, *keys: str) -> bool:
        return True
