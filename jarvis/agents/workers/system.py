"""System Workers — ♣ Suit.

v4.2.0: Enhanced with ComputerManager integration for safe OS control.
v4.4.0: Added application awareness — workers know which app they're controlling.
Workers NEVER directly control the OS — they go through the manager.
"""

import time
import logging
from .base import BaseWorker
from ...core.models import Suit, Rank

log = logging.getLogger("jarvis.workers.system")


class FilesWorker(BaseWorker):
    """♣ Queen — File Manager.

    v4.2.0: Routes all file operations through ComputerManager
    with permission checks and action logging.
    v4.4.0: Application awareness — knows how to interact with Finder
    via accessibility (semantic click/type instead of coordinates).
    """

    def __init__(self):
        super().__init__(suit=Suit.CLUBS, rank=Rank.QUEEN)

    @property
    def name(self) -> str:
        return "Files"

    @property
    def title(self) -> str:
        return "File Manager"

    def get_system_prompt(self) -> str:
        return """You are the File Manager (♣Q).
Specialize in: file operations, directory management, organization.
Focus on: safety, backup, clear naming, organization.

You have access to these file operations via the computer manager:
- file.read: Read a file's contents
- file.write: Create or overwrite a file
- file.delete: Delete a file (HIGH risk — requires confirmation)
- file.move: Move or rename a file
- file.list: List directory contents
- file.search: Search for files by pattern

You also have ACCESSIBILITY actions for interacting with Finder visually:
- accessibility.click("New Folder") — click buttons by name
- accessibility.type_into("search", "query") — type into text fields
- accessibility.find("Save") — find UI elements
- accessibility.activate("Finder") — bring Finder to front
- accessibility.summary() — see current UI state

When the user asks to interact with Finder's UI (not shell commands),
use accessibility actions instead of shell commands. This is faster
and more reliable than coordinates.

Always verify paths before destructive operations.
Prefer reading over writing when exploring.
Never delete without explicit user approval."""

    async def execute_file_action(self, action: str, **params) -> dict:
        """Execute a file action through the ComputerManager.

        This is the safe entry point for all file operations.
        """
        from ...computer.manager import computer_manager

        result = await computer_manager.execute(
            action=action,
            agent=self.card_id,
            **params,
        )
        return result.to_dict()

    async def interact_finder(self, query: str) -> dict:
        """Interact with Finder using semantic accessibility actions.

        Examples:
            await worker.interact_finder("click New Folder")
            await worker.interact_finder("type into search documents")
        """
        from ...computer.manager import computer_manager

        query_lower = query.lower().strip()

        # Parse intent
        if query_lower.startswith("click "):
            target = query[6:].strip()
            result = await computer_manager.execute(
                action="accessibility.click",
                query=target,
                agent=self.card_id,
            )
        elif query_lower.startswith("type ") or query_lower.startswith("type into "):
            parts = query.split(" ", 2)
            if len(parts) >= 3:
                target = parts[1] if "into" not in parts[0] else parts[2].split(" ", 1)[0]
                text = query.split(target)[-1].strip() if target in query else ""
                result = await computer_manager.execute(
                    action="accessibility.type_into",
                    query=target,
                    text=text,
                    agent=self.card_id,
                )
            else:
                result = await computer_manager.execute(
                    action="accessibility.find",
                    query=query,
                    agent=self.card_id,
                )
        elif query_lower.startswith("find "):
            target = query[5:].strip()
            result = await computer_manager.execute(
                action="accessibility.find",
                query=target,
                agent=self.card_id,
            )
        elif query_lower == "summary" or query_lower == "state":
            result = await computer_manager.execute(
                action="accessibility.summary",
                agent=self.card_id,
            )
        else:
            # Default: try to find the element
            result = await computer_manager.execute(
                action="accessibility.find",
                query=query,
                agent=self.card_id,
            )

        return result.to_dict()


class TerminalWorker(BaseWorker):
    """♣ Jack — Terminal Specialist.

    v4.2.0: Routes all terminal commands through ComputerManager
    with risk classification, permission checks, and action logging.
    v4.4.0: Application awareness — can interact with Terminal.app
    via accessibility, detect active terminal, and manage sessions.
    """

    def __init__(self):
        super().__init__(suit=Suit.CLUBS, rank=Rank.JACK)

    @property
    def name(self) -> str:
        return "Terminal"

    @property
    def title(self) -> str:
        return "Terminal Specialist"

    def get_system_prompt(self) -> str:
        return """You are the Terminal Specialist (♣J).
Specialize in: command line, shell scripts, automation, system commands.
Focus on: safety, efficiency, documentation, error handling.

You have access to terminal operations via the computer manager:
- terminal.run: Execute a shell command (risk-checked)
- terminal.run_safe: Execute in strict sandbox
- terminal.run_python: Execute Python code

You also have ACCESSIBILITY actions for interacting with Terminal.app visually:
- accessibility.click("New Tab") — click Terminal buttons by name
- accessibility.find("Shell") — find menu items
- accessibility.activate("Terminal") — bring Terminal to front
- accessibility.summary() — see current Terminal UI state

When the user asks to interact with Terminal's UI elements (menus, buttons),
use accessibility actions. For shell commands, use terminal.run.

Risk levels for commands:
- SAFE (auto-approve): ls, pwd, git status, reading files
- LOW (auto-approve): echo, cat, find, grep
- MEDIUM (notify): pip install, npm install, mkdir, touch
- HIGH (confirm): sudo, rm, kill, chmod
- DANGEROUS (block): rm -rf /, system modifications

Always explain what a command does before executing it.
Never run destructive commands without user confirmation.
Prefer safe mode for uncertain operations."""

    async def execute_terminal(self, command: str, timeout: int = 30) -> dict:
        """Execute a terminal command through the ComputerManager.

        This is the safe entry point for all terminal operations.
        The manager handles risk classification, permissions, and logging.
        """
        from ...computer.manager import computer_manager

        result = await computer_manager.execute(
            action="terminal.run",
            command=command,
            agent=self.card_id,
            timeout=timeout,
        )
        return result.to_dict()

    async def execute_safe(self, command: str, timeout: int = 30) -> dict:
        """Execute in strict sandbox mode."""
        from ...computer.manager import computer_manager

        result = await computer_manager.execute(
            action="terminal.run_safe",
            command=command,
            agent=self.card_id,
            timeout=timeout,
        )
        return result.to_dict()

    async def interact_terminal(self, query: str) -> dict:
        """Interact with Terminal.app using semantic accessibility actions.

        Examples:
            await worker.interact_terminal("click New Tab")
            await worker.interact_terminal("find Shell menu")
        """
        from ...computer.manager import computer_manager

        query_lower = query.lower().strip()

        if query_lower.startswith("click "):
            target = query[6:].strip()
            result = await computer_manager.execute(
                action="accessibility.click",
                query=target,
                agent=self.card_id,
            )
        elif query_lower.startswith("find "):
            target = query[5:].strip()
            result = await computer_manager.execute(
                action="accessibility.find",
                query=target,
                agent=self.card_id,
            )
        elif query_lower == "summary" or query_lower == "state":
            result = await computer_manager.execute(
                action="accessibility.summary",
                agent=self.card_id,
            )
        else:
            result = await computer_manager.execute(
                action="accessibility.find",
                query=query,
                agent=self.card_id,
            )

        return result.to_dict()


class ApplicationsWorker(BaseWorker):
    """♣ 10 — Application Manager.

    Manages application lifecycle and system resources.
    """

    def __init__(self):
        super().__init__(suit=Suit.CLUBS, rank=Rank.TEN)

    @property
    def name(self) -> str:
        return "Applications"

    @property
    def title(self) -> str:
        return "Application Manager"

    def get_system_prompt(self) -> str:
        return """You are the Application Manager (♣10).
Specialize in: application management, process control, system resources.
Focus on: performance, stability, resource efficiency.
Manage applications and system resources effectively."""
