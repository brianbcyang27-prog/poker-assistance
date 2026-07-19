"""Personal timeline data models."""
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class TimelineEventType(str, Enum):
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    DECISION_MADE = "decision_made"
    SKILL_LEARNED = "skill_learned"
    TECHNOLOGY_ADOPTED = "technology_adopted"
    GOAL_SET = "goal_set"
    GOAL_ACHIEVED = "goal_achieved"
    MILESTONE = "milestone"
    LESSON_LEARNED = "lesson_learned"
    PERSON_MET = "person_met"
    CUSTOM = "custom"


@dataclass
class TimelineEvent:
    id: str = ""
    title: str = ""
    description: str = ""
    event_type: str = "custom"
    date: str = ""  # YYYY-MM-DD
    timestamp: float = 0.0
    related_entities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    importance: str = "useful"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"event_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.date:
            self.date = time.strftime("%Y-%m-%d")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type,
            "date": self.date,
            "timestamp": self.timestamp,
            "related_entities": self.related_entities,
            "tags": self.tags,
            "importance": self.importance,
            "metadata": self.metadata,
        }


@dataclass
class TimelineQuery:
    start_date: str = ""
    end_date: str = ""
    event_types: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    related_entity: str = ""
    min_importance: str = ""
    limit: int = 50

    def to_dict(self) -> dict:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "event_types": self.event_types,
            "tags": self.tags,
            "related_entity": self.related_entity,
            "min_importance": self.min_importance,
            "limit": self.limit,
        }


@dataclass
class TimelineSummary:
    total_events: int = 0
    date_range: str = ""
    event_type_counts: Dict[str, int] = field(default_factory=dict)
    recent_events: List[TimelineEvent] = field(default_factory=list)
    milestones: List[TimelineEvent] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_events": self.total_events,
            "date_range": self.date_range,
            "event_type_counts": self.event_type_counts,
            "recent_count": len(self.recent_events),
            "milestones_count": len(self.milestones),
        }
