"""Mission replay data models."""
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class MissionEventType(str, Enum):
    STARTED = "started"
    RESEARCH = "research"
    PLAN = "plan"
    ACTION = "action"
    VERIFICATION = "verification"
    ERROR = "error"
    RECOVERY = "recovery"
    COMPLETED = "completed"
    FAILED = "failed"
    LESSON = "lesson"


@dataclass
class MissionEvent:
    id: str = ""
    mission_id: str = ""
    event_type: str = "action"
    title: str = ""
    description: str = ""
    timestamp: float = 0.0
    duration_ms: int = 0
    agent_id: str = ""
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"evt_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mission_id": self.mission_id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "agent_id": self.agent_id,
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass
class MissionReport:
    mission_id: str = ""
    goal: str = ""
    plan: str = ""
    actions: List[MissionEvent] = field(default_factory=list)
    problems: List[MissionEvent] = field(default_factory=list)
    verification: str = ""
    lessons: List[str] = field(default_factory=list)
    outcome: str = ""  # success, partial, failed
    duration_seconds: float = 0.0
    total_events: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "goal": self.goal,
            "plan": self.plan,
            "actions": [a.to_dict() for a in self.actions],
            "problems": [p.to_dict() for p in self.problems],
            "verification": self.verification,
            "lessons": self.lessons,
            "outcome": self.outcome,
            "duration_seconds": self.duration_seconds,
            "total_events": self.total_events,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    def to_timeline(self) -> List[Dict[str, Any]]:
        """Format as timeline for UI display."""
        all_events = self.actions + self.problems
        all_events.sort(key=lambda e: e.timestamp)
        return [{
            "time": time.strftime("%H:%M", time.localtime(e.timestamp)),
            "type": e.event_type,
            "title": e.title,
            "description": e.description[:200],
            "success": e.success,
        } for e in all_events]


@dataclass
class MissionReplayQuery:
    mission_id: str = ""
    event_types: List[str] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    agent_id: str = ""
    limit: int = 100

    def to_dict(self) -> dict:
        return {
            "mission_id": self.mission_id,
            "event_types": self.event_types,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "agent_id": self.agent_id,
            "limit": self.limit,
        }
