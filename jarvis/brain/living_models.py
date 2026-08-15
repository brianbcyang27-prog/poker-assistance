"""Living Intelligence Models - Data structures for the background brain loop."""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextSnapshot:
    """A point-in-time capture of the user's computing environment."""

    timestamp: float = field(default_factory=time.time)
    active_app: str = ""
    active_file: str = ""
    git_branch: str = ""
    browser_tabs: list[str] = field(default_factory=list)
    open_files: list[str] = field(default_factory=list)
    running_terminals: list[str] = field(default_factory=list)
    current_mission: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    context_dict: dict[str, Any] = field(default_factory=dict)


@dataclass
class Understanding:
    """Analysis of what's happening based on a context snapshot."""

    snapshot: ContextSnapshot = field(default_factory=ContextSnapshot)
    summary: str = ""
    detected_patterns: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    context_changes: list[str] = field(default_factory=list)


@dataclass
class Prediction:
    """A prediction about what the user might need next."""

    description: str = ""
    confidence: float = 0.0
    category: str = "work"
    timeframe: str = "immediate"


@dataclass
class PlannedAction:
    """An action the brain proposes to take."""

    action_type: str = "suggest"
    description: str = ""
    priority: int = 0
    auto_approve: bool = False
    confidence: float = 0.0


@dataclass
class ActionResult:
    """Result of executing a planned action."""

    action: PlannedAction = field(default_factory=PlannedAction)
    executed: bool = False
    result: str = ""
    timestamp: float = field(default_factory=time.time)
