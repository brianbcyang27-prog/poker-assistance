"""Living Dashboard data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class WorkerStatus:
    """Status of an active worker agent."""
    name: str
    role: str
    current_task: str
    confidence: float
    status: str  # active, idle, error
    last_active: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "current_task": self.current_task,
            "confidence": self.confidence,
            "status": self.status,
            "last_active": self.last_active,
        }


@dataclass
class ThoughtEntry:
    """A thought or prediction from the LivingBrain."""
    timestamp: str
    content: str
    category: str
    confidence: float
    actions_proposed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "content": self.content,
            "category": self.category,
            "confidence": self.confidence,
            "actions_proposed": self.actions_proposed,
        }


@dataclass
class DashboardStatus:
    """Full dashboard snapshot sent to the WebSocket UI."""
    timestamp: str
    neural_core_status: str
    mission_queue: List[Dict[str, Any]] = field(default_factory=list)
    thoughts: List[Dict[str, Any]] = field(default_factory=list)
    workers: List[Dict[str, Any]] = field(default_factory=list)
    recent_memories: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    current_project: str = ""
    system_metrics: Dict[str, Any] = field(default_factory=dict)
    uptime: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "neural_core_status": self.neural_core_status,
            "mission_queue": self.mission_queue,
            "thoughts": self.thoughts,
            "workers": self.workers,
            "recent_memories": self.recent_memories,
            "timeline": self.timeline,
            "suggestions": self.suggestions,
            "current_project": self.current_project,
            "system_metrics": self.system_metrics,
            "uptime": self.uptime,
        }
