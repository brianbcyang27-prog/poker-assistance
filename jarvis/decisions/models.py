"""Decision memory data models."""
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class DecisionImpact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVERSED = "reversed"
    ARCHIVED = "archived"


@dataclass
class Decision:
    id: str = ""
    title: str = ""
    description: str = ""
    reason: str = ""
    alternatives: List[str] = field(default_factory=list)
    chosen_option: str = ""
    impact: str = "medium"
    status: str = "active"
    date: str = ""  # YYYY-MM-DD
    timestamp: float = 0.0
    related_entities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    outcome: str = ""  # filled in later
    superseded_by: str = ""  # id of replacement decision

    def __post_init__(self):
        if not self.id:
            self.id = f"decision_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.date:
            self.date = time.strftime("%Y-%m-%d")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "reason": self.reason,
            "alternatives": self.alternatives,
            "chosen_option": self.chosen_option,
            "impact": self.impact,
            "status": self.status,
            "date": self.date,
            "timestamp": self.timestamp,
            "related_entities": self.related_entities,
            "tags": self.tags,
            "outcome": self.outcome,
            "superseded_by": self.superseded_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            reason=data.get("reason", ""),
            alternatives=data.get("alternatives", []),
            chosen_option=data.get("chosen_option", ""),
            impact=data.get("impact", "medium"),
            status=data.get("status", "active"),
            date=data.get("date", ""),
            timestamp=float(data.get("timestamp", 0.0)),
            related_entities=data.get("related_entities", []),
            tags=data.get("tags", []),
            outcome=data.get("outcome", ""),
            superseded_by=data.get("superseded_by", ""),
        )


@dataclass
class DecisionQuery:
    tags: List[str] = field(default_factory=list)
    impact: str = ""
    status: str = "active"
    related_entity: str = ""
    start_date: str = ""
    end_date: str = ""
    limit: int = 50

    def to_dict(self) -> dict:
        return {
            "tags": self.tags,
            "impact": self.impact,
            "status": self.status,
            "related_entity": self.related_entity,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "limit": self.limit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionQuery":
        return cls(
            tags=data.get("tags", []),
            impact=data.get("impact", ""),
            status=data.get("status", "active"),
            related_entity=data.get("related_entity", ""),
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date", ""),
            limit=int(data.get("limit", 50)),
        )
