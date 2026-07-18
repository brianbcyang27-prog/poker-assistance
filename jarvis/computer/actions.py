"""Action models for computer control.

Defines risk levels, action results, and action records
for the entire computer control subsystem.
"""

import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class RiskLevel(str, Enum):
    """Risk classification for computer actions."""
    SAFE = "safe"           # screenshots, reading, status checks
    LOW = "low"             # ls, pwd, git status, reading project files
    MEDIUM = "medium"       # pip install, npm install, modifying project files
    HIGH = "high"           # sudo, deleting files, changing system settings
    DANGEROUS = "dangerous" # deleting system folders, exposing secrets, modifying security


class ActionStatus(str, Enum):
    """Status of a computer action."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"


class ActionType(str, Enum):
    """Types of computer actions."""
    TERMINAL = "terminal"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    FILE_MOVE = "file_move"
    SCREENSHOT = "screenshot"
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    BROWSER = "browser"
    APP_LAUNCH = "app_launch"
    APP_CLOSE = "app_close"
    PROCESS = "process"
    SYSTEM = "system"
    VISION = "vision"           # v4.5.0 — vision analysis actions
    ACCESSIBILITY = "accessibility"  # v4.4.0 — accessibility actions
    OS = "os"                   # v5.0.0 — OS integration actions


@dataclass
class ActionResult:
    """Result of a single computer action execution."""
    action_id: str = ""
    action_type: str = ""
    command: str = ""
    status: str = ActionStatus.SUCCESS
    risk_level: str = RiskLevel.SAFE
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "command": self.command[:500],
            "status": self.status,
            "risk_level": self.risk_level,
            "output": self.output[:2000],
            "error": self.error[:1000],
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ActionRecord:
    """Persistent record of a computer action for audit and memory."""
    id: str = ""
    agent: str = ""          # which worker triggered this
    task_id: str = ""        # associated task
    action_type: str = ""
    command: str = ""
    risk_level: str = RiskLevel.SAFE
    status: str = ActionStatus.PENDING
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    approved_by: str = ""    # "auto", "user", "policy"
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.id:
            self.id = f"action_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent": self.agent,
            "task_id": self.task_id,
            "action_type": self.action_type,
            "command": self.command[:500],
            "risk_level": self.risk_level,
            "status": self.status,
            "output": self.output[:2000],
            "error": self.error[:1000],
            "duration_ms": round(self.duration_ms, 2),
            "approved_by": self.approved_by,
            "timestamp": self.timestamp,
        }

    def to_memory_string(self) -> str:
        """Compact string for memory storage."""
        status_icon = "✓" if self.status == ActionStatus.SUCCESS else "✗"
        return (
            f"{status_icon} [{self.action_type}] {self.command[:100]} "
            f"(risk={self.risk_level}, {self.duration_ms:.0f}ms)"
        )
