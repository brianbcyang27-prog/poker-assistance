"""Unified computer controller — handles browser, screen, mouse, search, AND project memory."""

import asyncio
import tempfile
import subprocess
from typing import Optional

from jarvis.core.reliability import config as reliability_config

from .browser import browser
from .mouse import mouse
from .screen import screen
from .search import web_search


class ComputerController:
    """Unified API for all computer interaction + project memory."""

    def __init__(self):
        self.browser = browser
        self.mouse = mouse
        self.screen = screen
        self.search = web_search
        self._initialized = False

    def list_actions(self) -> list[str]:
        """Return list of available action names."""
        return [
            "register_project", "list_projects", "get_active_project",
            "record_activity", "resume_project", "open_terminal",
            "browser_navigate", "browser_click", "browser_type",
            "browser_screenshot", "browser_get_text", "browser_scroll",
            "browser_press_key", "browser_evaluate",
            "screen_capture", "screen_capture_region", "screen_get_active_window",
            "screen_list_windows",
            "mouse_move", "mouse_click", "mouse_drag", "mouse_scroll",
            "keyboard_type", "keyboard_press", "keyboard_hotkey",
            "list_files", "read_file", "write_file", "create_file", "file_exists",
            "shell_execute", "web_search", "web_fetch",
            "arduino_send", "arduino_list",
        ]

    async def initialize(self):
        if not self._initialized:
            await self.browser.start(headless=True)
            self._initialized = True
        return True

    async def execute(self, action: str, **params) -> dict:
        """Execute an action."""
        if not self._initialized and action not in (
            "search", "open_url", "open_app",
            "register_project", "list_projects", "get_active_project",
            "record_activity", "resume_project", "open_terminal",
        ):
            await self.initialize()

        actions = {
            # Project Memory
            "register_project": self._register_project,
            "list_projects": self._list_projects,
            "get_active_project": self._get_active_project,
            "record_activity": self._record_activity,
            "resume_project": self._resume_project,
            "open_terminal": self._open_terminal,

            # Browser
            "browser_navigate": self._browser_navigate,
            "browser_click": self._browser_click,
            "browser_type": self._browser_type,
            "browser_screenshot": self._browser_screenshot,
            "browser_get_text": self._browser_get_text,
            "browser_scroll": self._browser_scroll,
            "browser_press_key": self._browser_press_key,
            "browser_evaluate": self._browser_evaluate,

            # Screen
            "screen_capture": self._screen_capture,
            "screen_capture_region": self._screen_capture_region,
            "screen_get_active_window": self._screen_get_active_window,
            "screen_list_windows": self._screen_list_windows,

            # Mouse/keyboard
            "mouse_click": self._mouse_click,
            "mouse_move": self._mouse_move,
            "mouse_double_click": self._mouse_double_click,
            "type_text": self._type_text,
            "hotkey": self._hotkey,
            "press_key": self._press_key,
            "scroll": self._scroll,
            "get_mouse_position": self._get_mouse_position,
            "get_screen_size": self._get_screen_size,

            # App
            "open_app": self._open_app,
            "open_url": self._open_url,

            # Files
            "list_files": self._list_files,
            "read_file": self._read_file,
            "write_file": self._write_file,
            "create_file": self._create_file,
            "file_exists": self._file_exists,

            # Shell
            "shell_execute": self._shell_execute,

            # Search
            "web_search": self._web_search,
            "web_fetch": self._web_fetch,

            # Workflow
            "task_complete": self._task_complete,
        }

        handler = actions.get(action)
        if not handler:
            return {"ok": False, "error": f"Unknown action: {action}"}

        try:
            return await handler(**params)
        except Exception as e:
            return {"ok": False, "error": str(e), "action": action}

    # ── Project Memory ─────────────────────────────────────────────

    async def _register_project(
        self,
        name: str = "",
        path: str = "",
        description: str = "",
        language: str = "",
        server_command: str = "",
        server_port: int = 0,
        url: str = "",
        ai_tool_command: str = "",
        ai_tool_name: str = "",
        **kw,
    ):
        from ..brain.project_memory import project_memory
        project = await project_memory.register_project(
            name=name,
            path=path,
            description=description,
            language=language,
            server_command=server_command,
            server_port=server_port,
            url=url,
            ai_tool_command=ai_tool_command,
            ai_tool_name=ai_tool_name,
        )
        return {"ok": True, "project": project}

    async def _list_projects(self, status: str = None, **kw):
        from ..brain.project_memory import project_memory
        projects = await project_memory.list_projects(status=status)
        return {"ok": True, "projects": projects}

    async def _get_active_project(self, **kw):
        from ..brain.project_memory import project_memory
        project = await project_memory.get_active_project()
        if project:
            return {"ok": True, "project": project}
        return {"ok": False, "error": "No active project"}

    async def _record_activity(self, name: str = "", **kw):
        from ..brain.project_memory import project_memory
        await project_memory.record_activity(name)
        return {"ok": True}

    async def _resume_project(self, name: str = None, **kw):
        """Resume a project: open terminal in project dir, browser, AI tool.
        
        Server is NOT auto-started — user runs it manually for stability.
        """
        from ..brain.project_memory import project_memory

        if name:
            project = await project_memory.get_project(name)
        else:
            project = await project_memory.get_active_project()

        if not project:
            return {"ok": False, "error": "No project found to resume"}

        await project_memory.record_activity(project["name"])

        commands = project_memory.build_resume_commands(project)
        if not commands:
            return {"ok": True, "message": "No auto-launch commands configured", "project": project["name"]}

        script = project_memory.build_resume_script(project)
        if not script:
            return {"ok": True, "message": "Nothing to launch", "project": project["name"]}

        # Write script to temp file and execute
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        proc = await asyncio.create_subprocess_shell(
            f"bash {script_path}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Run in background, don't block

        launched = [c["title"] for c in commands]
        hint = project.get("server_command", "")

        return {
            "ok": True,
            "project": project["name"],
            "launched": launched,
            "hint": f"Server not started — run: {hint}" if hint else None,
        }

    async def _open_terminal(self, command: str = "", title: str = "JARVIS", **kw):
        """Open a new macOS Terminal window with a command."""
        escaped_cmd = command.replace('"', '\\"')
        escaped_title = title.replace('"', '\\"')
        apple_script = (
            f'tell application "Terminal"\n'
            f'  activate\n'
            f'  do script "{escaped_cmd}"\n'
            f'  set custom title of front window to "{escaped_title}"\n'
            f'end tell'
        )
        proc = await asyncio.create_subprocess_shell(
            f"osascript -e '{apple_script}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {"ok": proc.returncode == 0, "title": title}

    # ── Browser ────────────────────────────────────────────────────

    async def _browser_navigate(self, url: str = "", **kw):
        return await self.browser.navigate(url)

    async def _browser_click(self, selector: str = "", **kw):
        return await self.browser.click(selector)

    async def _browser_type(self, selector: str = "", text: str = "", **kw):
        return await self.browser.type_text(selector, text)

    async def _browser_screenshot(self, name: str = None, **kw):
        return await self.browser.screenshot(name)

    async def _browser_get_text(self, **kw):
        return await self.browser.get_text()

    async def _browser_scroll(self, direction: str = "down", amount: int = 500, **kw):
        return await self.browser.scroll(direction, amount)

    async def _browser_press_key(self, key: str = "", **kw):
        return await self.browser.press_key(key)

    async def _browser_evaluate(self, expression: str = "", **kw):
        return await self.browser.evaluate(expression)

    # ── Screen ─────────────────────────────────────────────────────

    async def _screen_capture(self, name: str = None, **kw):
        return await self.screen.capture(name)

    async def _screen_capture_region(self, x: int = 0, y: int = 0, width: int = 800, height: int = 600, **kw):
        return await self.screen.capture_region(x, y, width, height)

    async def _screen_get_active_window(self, **kw):
        return await self.screen.get_active_window()

    async def _screen_list_windows(self, **kw):
        return await self.screen.list_windows()

    # ── Mouse/Keyboard ─────────────────────────────────────────────

    async def _mouse_click(self, x: int = 0, y: int = 0, button: str = "left", **kw):
        return await self.mouse.click(x, y, button)

    async def _mouse_move(self, x: int = 0, y: int = 0, **kw):
        return await self.mouse.move(x, y)

    async def _mouse_double_click(self, x: int = 0, y: int = 0, **kw):
        return await self.mouse.double_click(x, y)

    async def _type_text(self, text: str = "", **kw):
        return await self.mouse.type_text(text)

    async def _hotkey(self, keys: list = None, **kw):
        if not keys:
            return {"ok": False, "error": "No keys specified"}
        return await self.mouse.hotkey(*keys)

    async def _press_key(self, key: str = "", **kw):
        return await self.mouse.press_key(key)

    async def _scroll(self, direction: str = "down", amount: int = 3, **kw):
        return await self.mouse.scroll(amount)

    async def _get_mouse_position(self, **kw):
        return await self.mouse.get_mouse_position()

    async def _get_screen_size(self, **kw):
        return await self.mouse.get_screen_size()

    # ── Apps ───────────────────────────────────────────────────────

    async def _open_app(self, app_name: str = "", **kw):
        return await self.screen.open_app(app_name)

    async def _open_url(self, url: str = "", **kw):
        return await self.screen.open_url(url)

    # ── File Operations ───────────────────────────────────────────

    async def _list_files(self, path: str = ".", **kw):
        """List files in a directory."""
        from pathlib import Path
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return {"ok": False, "error": f"Path not found: {path}"}
            if not p.is_dir():
                return {"ok": False, "error": f"Not a directory: {path}"}
            items = []
            for item in sorted(p.iterdir()):
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "path": str(item),
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            return {"ok": True, "files": items, "count": len(items)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _read_file(self, path: str = "", max_size: int = 100000, **kw):
        """Read a file's contents."""
        from pathlib import Path
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return {"ok": False, "error": f"File not found: {path}"}
            if not p.is_file():
                return {"ok": False, "error": f"Not a file: {path}"}
            content = p.read_text(encoding="utf-8", errors="replace")[:max_size]
            return {"ok": True, "content": content, "size": p.stat().st_size}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _write_file(self, path: str = "", content: str = "", **kw):
        """Write content to a file."""
        from pathlib import Path
        try:
            p = Path(path).expanduser()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"ok": True, "path": str(p), "size": len(content)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _create_file(self, path: str = "", content: str = "", **kw):
        """Create a new file (alias for write_file)."""
        return await self._write_file(path=path, content=content, **kw)

    async def _file_exists(self, path: str = "", **kw):
        """Check if a file exists."""
        from pathlib import Path
        try:
            p = Path(path).expanduser()
            return {"ok": True, "exists": p.exists(), "path": str(p)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Shell ──────────────────────────────────────────────────────

    async def _shell_execute(self, command: str = "", **kw):
        """Execute a shell command and return output."""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=reliability_config.browser_timeout)
            return {
                "ok": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace")[:4000],
                "stderr": stderr.decode("utf-8", errors="replace")[:2000],
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            return {"ok": False, "error": "Command timed out (30s)"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Search ─────────────────────────────────────────────────────

    async def _web_search(self, query: str = "", engine: str = "duckduckgo", **kw):
        return await self.search.search(query, engine)

    async def _web_fetch(self, url: str = "", **kw):
        return await self.search.fetch_page(url)

    # ── Workflow ───────────────────────────────────────────────────

    async def _task_complete(self, summary: str = "", **kw):
        return {"ok": True, "task_complete": True, "summary": summary}

    async def shutdown(self):
        if self._initialized:
            await self.browser.stop()
            self._initialized = False


controller = ComputerController()
