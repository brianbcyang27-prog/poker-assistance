"""System Workers — ♣ Suit.

v4.2.0: Enhanced with ComputerManager integration for safe OS control.
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


class TerminalWorker(BaseWorker):
    """♣ Jack — Terminal Specialist.

    v4.2.0: Routes all terminal commands through ComputerManager
    with risk classification, permission checks, and action logging.
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
