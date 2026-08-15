"""Unified computer controller — facade over the ComputerManager execution engine.

Every action executes through ComputerManager (risk classification → permission
check → handler → audit log → DB store → event emission), so no action bypasses
the permission system or the activity stream. The controller keeps the flat,
worker-friendly action names and alias normalization on top of the manager.
"""

import asyncio
import tempfile

from jarvis.core.reliability import CircuitBreakerOpenError, circuit_breaker
from jarvis.core.reliability import config as reliability_config

from .actions import ActionStatus, RiskLevel
from .browser import browser
from .mouse import mouse
from .screen import screen
from .search import web_search

# Risk classification per flat controller action. Browser/mouse/keyboard actions
# are LOW (classify_risk also inspects the command string), screen/file-reads
# are SAFE, file writes are MEDIUM.
_ACTION_RISKS = {
    "register_project": RiskLevel.LOW,
    "list_projects": RiskLevel.SAFE,
    "get_active_project": RiskLevel.SAFE,
    "record_activity": RiskLevel.SAFE,
    "resume_project": RiskLevel.LOW,
    "open_terminal": RiskLevel.LOW,
    "browser_navigate": RiskLevel.LOW,
    "browser_click": RiskLevel.LOW,
    "browser_type": RiskLevel.LOW,
    "browser_screenshot": RiskLevel.SAFE,
    "browser_get_text": RiskLevel.SAFE,
    "browser_scroll": RiskLevel.LOW,
    "browser_press_key": RiskLevel.LOW,
    "browser_evaluate": RiskLevel.LOW,
    "screen_capture": RiskLevel.SAFE,
    "screen_capture_region": RiskLevel.SAFE,
    "screen_get_active_window": RiskLevel.SAFE,
    "screen_list_windows": RiskLevel.SAFE,
    "mouse_click": RiskLevel.LOW,
    "mouse_move": RiskLevel.LOW,
    "mouse_double_click": RiskLevel.LOW,
    "type_text": RiskLevel.LOW,
    "hotkey": RiskLevel.LOW,
    "press_key": RiskLevel.LOW,
    "scroll": RiskLevel.LOW,
    "get_mouse_position": RiskLevel.SAFE,
    "get_screen_size": RiskLevel.SAFE,
    "open_app": RiskLevel.LOW,
    "open_url": RiskLevel.LOW,
    "list_files": RiskLevel.SAFE,
    "read_file": RiskLevel.SAFE,
    "write_file": RiskLevel.MEDIUM,
    "create_file": RiskLevel.MEDIUM,
    "file_exists": RiskLevel.SAFE,
    "shell_execute": RiskLevel.LOW,
    "run_python": RiskLevel.LOW,
    "web_search": RiskLevel.SAFE,
    "web_fetch": RiskLevel.SAFE,
    "task_complete": RiskLevel.SAFE,
}


class ComputerController:
    """Unified API for all computer interaction + project memory."""

    def __init__(self):
        self.browser = browser
        self.mouse = mouse
        self.screen = screen
        self.search = web_search
        self._initialized = False
        self._snapshot_history: list[dict] = []
        self._snapshot_max = 200
        self._manager = None
        self._register_with_manager()

    @property
    def _engine(self):
        if self._manager is None:
            from .manager import computer_manager

            self._manager = computer_manager
        return self._manager

    def _register_with_manager(self):
        """Register every flat action handler on the shared manager engine."""
        for name, handler in self._action_handlers().items():
            self._engine.register(
                name,
                handler,
                risk_level=_ACTION_RISKS.get(name, RiskLevel.LOW),
                description=handler.__doc__ or name,
            )

    def list_actions(self) -> list[str]:
        """Return list of available action names."""
        return list(self._action_handlers().keys())

    async def initialize(self):
        if not self._initialized:
            await self.browser.start(headless=True)
            self._initialized = True
        return True

    def _action_handlers(self) -> dict:
        """Return the flat action name → handler map."""
        return {
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
            "run_python": self._run_python,
            # Search
            "web_search": self._web_search,
            "web_fetch": self._web_fetch,
            # Workflow
            "task_complete": self._task_complete,
        }

    async def execute(self, action: str, agent: str = "", **params) -> dict:
        """Execute an action through the manager's permission-gated pipeline."""
        action = self._normalize_action(action)
        if not self._initialized and action.startswith("browser_"):
            try:
                await self.initialize()
            except Exception as e:
                return {"ok": False, "error": f"Browser unavailable: {e}"}

        if action not in self._action_handlers():
            return {"ok": False, "error": f"Unknown action: {action}"}

        try:
            # Pre-action snapshot
            await self._capture_snapshot(action, params)
            async with circuit_breaker(
                f"tool:{action}", failure_threshold=3, recovery_timeout=30.0
            ):
                result = await self._engine.execute(
                    action=action, agent=agent, **params
                )
        except CircuitBreakerOpenError:
            return {
                "ok": False,
                "error": f"Tool '{action}' is temporarily disabled (circuit breaker open)",
                "circuit_open": True,
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "action": action}

        return self._result_to_dict(result)

    def _result_to_dict(self, result) -> dict:
        """Convert an ActionResult to the flat dict contract callers expect.

        The handler's raw dict is preserved in metadata["result"] so workers
        keep receiving the same fields (stdout, files, project, ...).
        """
        raw = dict((result.metadata or {}).get("result", {}) or {})
        out = {"ok": result.status == ActionStatus.SUCCESS}
        out.update(raw)
        out["action_id"] = result.action_id
        out["status"] = result.status
        out["risk_level"] = result.risk_level
        out["duration_ms"] = round(result.duration_ms, 2)
        if not out["ok"]:
            out["error"] = result.error or raw.get("error") or f"Action failed: {result.action_type}"
        return out

    def _normalize_action(self, action: str) -> str:
        """Map common worker/tool aliases to controller actions."""
        aliases = {
            "keyboard_type": "type_text",
            "keyboard_press": "press_key",
            "keyboard_hotkey": "hotkey",
            "browser_text": "browser_get_text",
            "browser_fill": "browser_type",
            "screen_active_window": "screen_get_active_window",
            "screen_open_app": "open_app",
            "screen_open_url": "open_url",
            "browser_open_app": "open_app",
            "browser_open_url": "open_url",
            "file_list": "list_files",
            "file_read": "read_file",
            "file_write": "write_file",
            "file_create": "create_file",
        }
        return aliases.get(action, action)

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
            return {
                "ok": True,
                "message": "No auto-launch commands configured",
                "project": project["name"],
            }

        script = project_memory.build_resume_script(project)
        if not script:
            return {"ok": True, "message": "Nothing to launch", "project": project["name"]}

        # Write script to temp file and execute
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(script)
            f.flush()
            script_path = f.name

        await asyncio.create_subprocess_shell(
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
            f"  activate\n"
            f'  do script "{escaped_cmd}"\n'
            f'  set custom title of front window to "{escaped_title}"\n'
            f"end tell"
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

    async def _screen_capture_region(
        self, x: int = 0, y: int = 0, width: int = 800, height: int = 600, **kw
    ):
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

        if not self._engine.permissions.is_path_allowed(path):
            return {"ok": False, "error": f"Path not allowed: {path}"}
        try:
            p = Path(path).expanduser()
            if not p.exists():
                return {"ok": False, "error": f"Path not found: {path}"}
            if not p.is_dir():
                return {"ok": False, "error": f"Not a directory: {path}"}
            items = []
            for item in sorted(p.iterdir()):
                items.append(
                    {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "path": str(item),
                        "size": item.stat().st_size if item.is_file() else 0,
                    }
                )
            return {"ok": True, "files": items, "count": len(items)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _read_file(self, path: str = "", max_size: int = 100000, **kw):
        """Read a file's contents."""
        from pathlib import Path

        if not self._engine.permissions.is_path_allowed(path):
            return {"ok": False, "error": f"Path not allowed: {path}"}
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

        if not self._engine.permissions.is_path_allowed(path):
            return {"ok": False, "error": f"Path not allowed: {path}"}
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

        if not self._engine.permissions.is_path_allowed(path):
            return {"ok": False, "error": f"Path not allowed: {path}"}
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
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=reliability_config.browser_timeout
            )
            return {
                "ok": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace")[:4000],
                "stderr": stderr.decode("utf-8", errors="replace")[:2000],
                "returncode": proc.returncode,
            }
        except TimeoutError:
            return {"ok": False, "error": "Command timed out (30s)"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _run_python(self, code: str = "", timeout: int = 30, **kw):
        """Execute Python code in a temp file and return output."""
        import os

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                script_path = f.name
            try:
                proc = await asyncio.create_subprocess_shell(
                    f"python3 {script_path}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                return {
                    "ok": proc.returncode == 0,
                    "stdout": stdout.decode("utf-8", errors="replace")[:4000],
                    "stderr": stderr.decode("utf-8", errors="replace")[:2000],
                    "returncode": proc.returncode,
                }
            finally:
                os.unlink(script_path)
        except TimeoutError:
            return {"ok": False, "error": f"Python execution timed out ({timeout}s)"}
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

    async def _capture_snapshot(self, action: str, params: dict) -> None:
        """Capture pre-action state snapshot (best-effort — failures and timeouts are silently caught)."""
        snapshot: dict = {
            "timestamp": __import__("time").time(),
            "action": action,
            "params": {k: v for k, v in params.items() if k != "password"},
        }
        try:
            window = await asyncio.wait_for(self.screen.get_active_window(), timeout=2)
            if isinstance(window, dict):
                snapshot["active_window"] = window.get("title", "") or window.get("app", "")
        except Exception:
            pass
        if self._initialized:
            try:
                ss = await asyncio.wait_for(self.screen.capture(name=f"pre_{action}"), timeout=2)
                if isinstance(ss, dict) and ss.get("path"):
                    snapshot["screenshot"] = ss["path"]
            except Exception:
                pass
        self._snapshot_history.append(snapshot)
        if len(self._snapshot_history) > self._snapshot_max:
            self._snapshot_history.pop(0)

    def get_snapshots(self, limit: int = 50) -> list[dict]:
        """Return the most recent pre-action snapshots."""
        return list(self._snapshot_history[-limit:])

    async def shutdown(self):
        if self._initialized:
            await self.browser.stop()
            self._initialized = False


controller = ComputerController()
