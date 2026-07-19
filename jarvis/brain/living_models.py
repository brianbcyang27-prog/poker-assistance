"""Living Intelligence Models - Data structures for the background brain loop."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContextSnapshot:
    """A point-in-time capture of the user's computing environment."""

    timestamp: float = field(default_factory=time.time)
    active_app: str = ""
    active_file: str = ""
    git_branch: str = ""
    browser_tabs: List[str] = field(default_factory=list)
    open_files: List[str] = field(default_factory=list)
    running_terminals: List[str] = field(default_factory=list)
    current_mission: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    context_dict: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Understanding:
    """Analysis of what's happening based on a context snapshot."""

    snapshot: ContextSnapshot = field(default_factory=ContextSnapshot)
    summary: str = ""
    detected_patterns: List[str] = field(default_factory=list)
    anomalies: List[str] = field(default_factory=list)
    context_changes: List[str] = field(default_factory=list)


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
