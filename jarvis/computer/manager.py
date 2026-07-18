"""Computer Manager — Central gateway for all computer control.

Every computer action goes through this manager:
  Agent → ComputerManager → Security Check → Execution → Logging → Memory

Responsibilities:
  - Route requests to the correct handler
  - Apply permission checks before execution
  - Log every action to database + memory
  - Emit events for UI updates
  - Provide unified API for all computer interaction

Usage:
    from jarvis.computer import computer_manager
    result = await computer_manager.execute(
        action="terminal.run",
        command="python app.py",
        agent="♣J",
    )
"""

import time
import logging
from typing import Optional, Callable, Any
from dataclasses import dataclass, field

from .actions import RiskLevel, ActionStatus, ActionType, ActionResult, ActionRecord
from .permissions import PermissionSystem, PermissionDecision
from .sandbox import Sandbox, SandboxResult
from .observer import ScreenObserver

log = logging.getLogger("jarvis.computer.manager")


@dataclass
class ActionHandler:
    """Registered handler for an action type."""
    name: str
    handler: Callable
    risk_level: str = RiskLevel.LOW
    description: str = ""


class ComputerManager:
    """Central gateway for all computer control.

    All computer actions must go through this manager.
    Workers should NEVER directly control the OS.

    Flow:
        1. Agent requests action
        2. Manager looks up handler
        3. Permission system checks risk
        4. If approved, handler executes
        5. Result is logged to database
        6. Event is emitted for UI
        7. Memory stores the action
    """

    def __init__(self):
        self.permissions = PermissionSystem()
        self.sandbox = Sandbox()
        self.observer = ScreenObserver()
        self._handlers: dict[str, ActionHandler] = {}
        self._action_log: list[ActionRecord] = []
        self._initialized = False
        self._provider = None

        # Register built-in handlers
        self._register_defaults()

    def _register_defaults(self):
        """Register default action handlers."""
        # Terminal actions
        self.register("terminal.run", self._terminal_run, RiskLevel.LOW, "Execute shell command")
        self.register("terminal.run_safe", self._terminal_run_safe, RiskLevel.SAFE, "Execute in sandbox")
        self.register("terminal.run_python", self._terminal_run_python, RiskLevel.LOW, "Execute Python code")

        # File actions
        self.register("file.read", self._file_read, RiskLevel.SAFE, "Read a file")
        self.register("file.write", self._file_write, RiskLevel.MEDIUM, "Write a file")
        self.register("file.delete", self._file_delete, RiskLevel.HIGH, "Delete a file")
        self.register("file.move", self._file_move, RiskLevel.MEDIUM, "Move/rename a file")
        self.register("file.list", self._file_list, RiskLevel.SAFE, "List directory contents")
        self.register("file.search", self._file_search, RiskLevel.SAFE, "Search for files")

        # Screen actions
        self.register("screen.screenshot", self._screen_screenshot, RiskLevel.SAFE, "Take screenshot")
        self.register("screen.state", self._screen_state, RiskLevel.SAFE, "Get screen state")
        self.register("screen.active_window", self._screen_active_window, RiskLevel.SAFE, "Get active window")
        self.register("screen.windows", self._screen_windows, RiskLevel.SAFE, "List windows")

        # Mouse/keyboard actions
        self.register("mouse.click", self._mouse_click, RiskLevel.LOW, "Click at coordinates")
        self.register("mouse.move", self._mouse_move, RiskLevel.LOW, "Move mouse")
        self.register("keyboard.type", self._keyboard_type, RiskLevel.LOW, "Type text")
        self.register("keyboard.press", self._keyboard_press, RiskLevel.LOW, "Press a key")
        self.register("keyboard.hotkey", self._keyboard_hotkey, RiskLevel.LOW, "Keyboard shortcut")

        # App actions
        self.register("app.open", self._app_open, RiskLevel.LOW, "Open an application")
        self.register("app.close", self._app_close, RiskLevel.MEDIUM, "Close an application")

        # Accessibility actions (v4.4.0 — semantic UI control)
        self.register("accessibility.tree", self._accessibility_tree, RiskLevel.SAFE, "Get UI element tree")
        self.register("accessibility.find", self._accessibility_find, RiskLevel.SAFE, "Find UI element by name")
        self.register("accessibility.click", self._accessibility_click, RiskLevel.LOW, "Click UI element by name")
        self.register("accessibility.type_into", self._accessibility_type_into, RiskLevel.LOW, "Type into UI element")
        self.register("accessibility.activate", self._accessibility_activate, RiskLevel.LOW, "Activate/bring app to front")
        self.register("accessibility.apps", self._accessibility_apps, RiskLevel.SAFE, "List running applications")
        self.register("accessibility.summary", self._accessibility_summary, RiskLevel.SAFE, "Get LLM-ready UI summary")

    def register(self, name: str, handler: Callable, risk_level: str = RiskLevel.LOW, description: str = ""):
        """Register an action handler."""
        self._handlers[name] = ActionHandler(
            name=name, handler=handler, risk_level=risk_level, description=description,
        )

    async def execute(
        self,
        action: str,
        agent: str = "",
        task_id: str = "",
        auto_approve: bool = False,
        **params,
    ) -> ActionResult:
        """Execute a computer action through the security pipeline.

        Args:
            action: Action name (e.g., "terminal.run")
            agent: Which agent is requesting (e.g., "♣J")
            task_id: Associated task ID
            auto_approve: Skip confirmation for MEDIUM risk (still blocks DANGEROUS)
            **params: Action-specific parameters

        Returns:
            ActionResult with status, output, timing
        """
        action_id = f"action_{int(time.time() * 1000)}_{hash(action) % 10000:04d}"
        start = time.time()

        # Look up handler
        handler_info = self._handlers.get(action)
        if not handler_info:
            return ActionResult(
                action_id=action_id,
                action_type=action,
                status=ActionStatus.FAILED,
                error=f"Unknown action: {action}",
            )

        # Build command string for risk analysis
        command = params.get("command", "") or params.get("text", "") or action

        # Permission check
        decision = self.permissions.check(
            command=command,
            action_type=self._action_type_from_name(action),
            agent=agent,
        )

        # Handle permission decisions
        if decision.requires_approval and not auto_approve:
            if decision.risk_level == RiskLevel.DANGEROUS:
                log.warning(f"BLOCKED dangerous action: {action} by {agent}")
                return ActionResult(
                    action_id=action_id,
                    action_type=action,
                    status=ActionStatus.BLOCKED,
                    risk_level=decision.risk_level,
                    error=decision.reason,
                    duration_ms=(time.time() - start) * 1000,
                )
            # HIGH risk needs confirmation — in automated mode, deny
            log.warning(f"Denied high-risk action without confirmation: {action}")
            return ActionResult(
                action_id=action_id,
                action_type=action,
                status=ActionStatus.DENIED,
                risk_level=decision.risk_level,
                error=f"Requires confirmation: {decision.reason}",
                duration_ms=(time.time() - start) * 1000,
            )

        # Execute
        self.set_state(AgentState.WORKING) if hasattr(self, 'set_state') else None

        try:
            result = await handler_info.handler(**params)
            duration = (time.time() - start) * 1000

            action_result = ActionResult(
                action_id=action_id,
                action_type=action,
                command=command[:500],
                status=ActionStatus.SUCCESS if result.get("ok", True) else ActionStatus.FAILED,
                risk_level=decision.risk_level,
                output=str(result.get("stdout", result.get("output", "")))[:4000],
                error=str(result.get("stderr", result.get("error", "")))[:2000],
                duration_ms=duration,
                metadata={"agent": agent, "task_id": task_id},
            )

        except Exception as e:
            duration = (time.time() - start) * 1000
            action_result = ActionResult(
                action_id=action_id,
                action_type=action,
                command=command[:500],
                status=ActionStatus.FAILED,
                risk_level=decision.risk_level,
                error=str(e),
                duration_ms=duration,
            )

        # Log action
        record = ActionRecord(
            id=action_id,
            agent=agent,
            task_id=task_id,
            action_type=action,
            command=command[:500],
            risk_level=decision.risk_level,
            status=action_result.status,
            output=action_result.output[:2000],
            error=action_result.error[:1000],
            duration_ms=action_result.duration_ms,
            approved_by=decision.approved_by if hasattr(decision, 'approved_by') else "auto",
        )
        self._action_log.append(record)

        # Keep only last 1000 in memory
        if len(self._action_log) > 1000:
            self._action_log = self._action_log[-500:]

        # Emit event
        await self._emit_event(action, action_result, agent)

        # Store in database
        await self._store_action(record)

        log.info(f"Action {action}: {action_result.status} ({action_result.duration_ms:.0f}ms)")
        return action_result

    async def _emit_event(self, action: str, result: ActionResult, agent: str):
        """Emit a computer action event."""
        try:
            from ..core.events import event_bus, Event
            event_type = f"computer.action.{'completed' if result.status == ActionStatus.SUCCESS else 'failed'}"
            await event_bus.emit(Event(
                type=event_type,
                data={
                    "action": action,
                    "status": result.status,
                    "risk_level": result.risk_level,
                    "duration_ms": result.duration_ms,
                    "agent": agent,
                },
                source=agent or "computer",
            ))
        except Exception:
            pass

    async def _store_action(self, record: ActionRecord):
        """Store action record in database."""
        try:
            from ..core.database import get_db
            db = await get_db()
            conn = db._db  # raw aiosqlite connection
            await conn.execute(
                """INSERT INTO action_log
                   (id, agent, task_id, action_type, command, risk_level,
                    status, output, error, duration_ms, approved_by, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.id, record.agent, record.task_id,
                    record.action_type, record.command, record.risk_level,
                    record.status, record.output, record.error,
                    record.duration_ms, record.approved_by, record.timestamp,
                ),
            )
            await conn.commit()
        except Exception as e:
            log.debug(f"Failed to store action: {e}")

    def _action_type_from_name(self, action: str) -> str:
        """Map action name to ActionType."""
        if action.startswith("terminal"):
            return ActionType.TERMINAL
        if action.startswith("file.read") or action.startswith("file.list") or action.startswith("file.search"):
            return ActionType.FILE_READ
        if action.startswith("file.write"):
            return ActionType.FILE_WRITE
        if action.startswith("file.delete"):
            return ActionType.FILE_DELETE
        if action.startswith("file.move"):
            return ActionType.FILE_MOVE
        if action.startswith("screen"):
            return ActionType.SCREENSHOT
        if action.startswith("mouse"):
            return ActionType.MOUSE
        if action.startswith("keyboard"):
            return ActionType.KEYBOARD
        if action.startswith("app"):
            return ActionType.APP_LAUNCH
        return ActionType.TERMINAL

    # ── Action Handlers ──────────────────────────────────────

    async def _terminal_run(self, command: str = "", timeout: int = 30, **kw) -> dict:
        """Execute a shell command."""
        result = await self.sandbox.run(command, timeout=timeout)
        return {
            "ok": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "duration_ms": result.duration_ms,
        }

    async def _terminal_run_safe(self, command: str = "", timeout: int = 30, **kw) -> dict:
        """Execute in strict sandbox."""
        result = await self.sandbox.run_safe(command, timeout=timeout)
        return {
            "ok": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    async def _terminal_run_python(self, code: str = "", timeout: int = 30, **kw) -> dict:
        """Execute Python code."""
        result = await self.sandbox.run_python(code, timeout=timeout)
        return {
            "ok": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }

    async def _file_read(self, path: str = "", **kw) -> dict:
        """Read a file."""
        import os
        if not self.permissions.is_path_allowed(path):
            return {"ok": False, "error": f"Path not allowed: {path}"}
        try:
            with open(os.path.expanduser(path), "r", errors="replace") as f:
                content = f.read(100_000)
            return {"ok": True, "output": content, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _file_write(self, path: str = "", content: str = "", **kw) -> dict:
        """Write to a file."""
        import os
        if not self.permissions.is_path_allowed(path):
            return {"ok": False, "error": f"Path not allowed: {path}"}
        try:
            os.makedirs(os.path.dirname(os.path.expanduser(path)), exist_ok=True)
            with open(os.path.expanduser(path), "w") as f:
                f.write(content)
            return {"ok": True, "path": path, "bytes": len(content)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _file_delete(self, path: str = "", **kw) -> dict:
        """Delete a file."""
        import os
        if not self.permissions.is_path_allowed(path):
            return {"ok": False, "error": f"Path not allowed: {path}"}
        try:
            os.remove(os.path.expanduser(path))
            return {"ok": True, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _file_move(self, source: str = "", destination: str = "", **kw) -> dict:
        """Move/rename a file."""
        import shutil
        if not self.permissions.is_path_allowed(source) or not self.permissions.is_path_allowed(destination):
            return {"ok": False, "error": "Path not allowed"}
        try:
            shutil.move(os.path.expanduser(source), os.path.expanduser(destination))
            return {"ok": True, "source": source, "destination": destination}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _file_list(self, path: str = ".", **kw) -> dict:
        """List directory contents."""
        import os
        try:
            entries = []
            for entry in os.scandir(os.path.expanduser(path)):
                entries.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else 0,
                })
            sorted_entries = sorted(entries, key=lambda e: (e["type"], e["name"]))
            listing = "\n".join(f"{'d' if e['type']=='dir' else 'f'} {e['name']}" for e in sorted_entries)
            return {"ok": True, "output": listing, "entries": sorted_entries, "path": path}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _file_search(self, pattern: str = "", path: str = ".", **kw) -> dict:
        """Search for files matching a pattern."""
        import glob
        import os
        try:
            search_path = os.path.join(os.path.expanduser(path), "**", pattern)
            matches = glob.glob(search_path, recursive=True)[:50]
            return {"ok": True, "matches": matches, "count": len(matches)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _screen_screenshot(self, path: str = None, **kw) -> dict:
        """Take a screenshot."""
        return await self.observer.take_screenshot(path) or {"ok": False, "error": "Screenshot failed"}

    async def _screen_state(self, capture: bool = False, **kw) -> dict:
        """Get screen state."""
        state = await self.observer.get_state(capture_screenshot=capture)
        return {"ok": True, **state.to_dict()}

    async def _screen_active_window(self, **kw) -> dict:
        """Get active window."""
        window = await self.observer.get_active_window()
        if window:
            return {"ok": True, **window.to_dict()}
        return {"ok": False, "error": "Could not detect active window"}

    async def _screen_windows(self, **kw) -> dict:
        """List all windows."""
        windows = await self.observer.list_windows()
        return {"ok": True, "windows": [w.to_dict() for w in windows]}

    async def _mouse_click(self, x: int = 0, y: int = 0, button: str = "left", **kw) -> dict:
        """Click at coordinates."""
        provider = self._get_provider()
        if provider:
            return await provider.click(x, y, button)
        return {"ok": False, "error": "No platform provider"}

    async def _mouse_move(self, x: int = 0, y: int = 0, **kw) -> dict:
        """Move mouse to coordinates."""
        provider = self._get_provider()
        if provider:
            return await provider.click(x, y)  # click moves then clicks
        return {"ok": False, "error": "No platform provider"}

    async def _keyboard_type(self, text: str = "", **kw) -> dict:
        """Type text."""
        provider = self._get_provider()
        if provider:
            return await provider.type_text(text)
        return {"ok": False, "error": "No platform provider"}

    async def _keyboard_press(self, key: str = "", **kw) -> dict:
        """Press a key."""
        provider = self._get_provider()
        if provider:
            return await provider.press_key(key)
        return {"ok": False, "error": "No platform provider"}

    async def _keyboard_hotkey(self, keys: list = None, **kw) -> dict:
        """Press keyboard shortcut."""
        provider = self._get_provider()
        if provider and keys:
            return await provider.hotkey(*keys)
        return {"ok": False, "error": "No platform provider or no keys"}

    async def _app_open(self, app_name: str = "", **kw) -> dict:
        """Open an application."""
        provider = self._get_provider()
        if provider:
            return await provider.open_app(app_name)
        return {"ok": False, "error": "No platform provider"}

    async def _app_close(self, app_name: str = "", **kw) -> dict:
        """Close an application."""
        provider = self._get_provider()
        if provider:
            return await provider.close_app(app_name)
        return {"ok": False, "error": "No platform provider"}

    def _get_provider(self):
        """Get the platform provider."""
        if self._provider:
            return self._provider
        try:
            from .providers import platform_provider
            self._provider = platform_provider
            return self._provider
        except Exception:
            return None

    def _get_accessibility(self):
        """Get the accessibility manager, initializing if needed."""
        if not hasattr(self, '_accessibility'):
            from .accessibility import accessibility_manager
            self._accessibility = accessibility_manager
        return self._accessibility

    # ── Accessibility Handlers (v4.4.0) ───────────────────────

    async def _accessibility_tree(self, window_title: str = "", **kw) -> dict:
        """Get the UI element tree for a window."""
        am = self._get_accessibility()
        await am.initialize()
        tree = await am.get_tree(window_title)
        return {"ok": True, **tree.to_dict()}

    async def _accessibility_find(self, query: str = "", **kw) -> dict:
        """Find a UI element by natural language query."""
        am = self._get_accessibility()
        await am.initialize()
        element = await am.find(query)
        if element:
            return {"ok": True, "element": element.to_dict()}
        return {"ok": False, "error": f"No element found matching '{query}'"}

    async def _accessibility_click(self, query: str = "", **kw) -> dict:
        """Click a UI element by natural language query."""
        am = self._get_accessibility()
        await am.initialize()
        result = await am.click(query)
        return result

    async def _accessibility_type_into(self, query: str = "", text: str = "", **kw) -> dict:
        """Type text into a UI element found by natural language query."""
        am = self._get_accessibility()
        await am.initialize()
        result = await am.type_into(query, text)
        return result

    async def _accessibility_activate(self, app_name: str = "", **kw) -> dict:
        """Bring an application to the foreground."""
        am = self._get_accessibility()
        await am.initialize()
        return await am.activate(app_name)

    async def _accessibility_apps(self, **kw) -> dict:
        """List running applications."""
        am = self._get_accessibility()
        await am.initialize()
        apps = await am.list_apps()
        return {"ok": True, "applications": apps}

    async def _accessibility_summary(self, window_title: str = "", **kw) -> dict:
        """Get an LLM-ready summary of the current UI state."""
        am = self._get_accessibility()
        await am.initialize()
        summary = await am.get_summary(window_title)
        return {"ok": True, "summary": summary}

    def get_actions(self) -> list[dict]:
        """List all registered actions."""
        return [
            {"name": h.name, "risk_level": h.risk_level, "description": h.description}
            for h in self._handlers.values()
        ]

    def get_recent_actions(self, limit: int = 20) -> list[dict]:
        """Get recent action records."""
        return [r.to_dict() for r in self._action_log[-limit:]]

    def get_stats(self) -> dict:
        """Get manager statistics."""
        return {
            "actions_registered": len(self._handlers),
            "actions_logged": len(self._action_log),
            "permissions": self.permissions.get_stats(),
        }

    async def shutdown(self):
        """Clean up resources."""
        self.sandbox.cleanup()


# Module-level singleton
computer_manager = ComputerManager()
