"""Context Engine Models - Data structures for environment tracking."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CurrentContext:
    """Full snapshot of the user's current computing state."""

    timestamp: float = field(default_factory=time.time)
    active_app: str = ""
    active_file: str = ""
    git_branch: str = ""
    git_repo: str = ""
    browser_tabs: List[str] = field(default_factory=list)
    open_files: List[str] = field(default_factory=list)
    running_terminals: List[str] = field(default_factory=list)
    current_mission: str = ""
    connected_devices: List[str] = field(default_factory=list)
    recent_conversations: List[str] = field(default_factory=list)
    current_project: str = ""
    current_language: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    uptime_seconds: float = 0.0
    context_dict: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimelineEvent:
    """A single event in the context timeline."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    category: str = "system"
    action: str = "observed"
    detail: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextSummary:
    """Human-readable summary of the current context."""

    timestamp: float = field(default_factory=time.time)
    active_project: str = ""
    today_events_count: int = 0
    active_apps: List[str] = field(default_factory=list)
    recent_files: List[str] = field(default_factory=list)
    recent_commits: List[str] = field(default_factory=list)
    current_focus: str = ""
    outstanding_tasks: List[str] = field(default_factory=list)
