"""Data models for the JARVIS Daily Journal & Weekly Review system."""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class EventCategory(enum.Enum):
    """Categories of journal events."""
    CODE = "code"
    COMMIT = "commit"
    BUG = "bug"
    FEATURE = "feature"
    RESEARCH = "research"
    MEETING = "meeting"
    BREAK = "break"


@dataclass
class JournalEvent:
    """Represents a single event logged in the daily journal."""
    timestamp: datetime
    category: EventCategory
    description: str
    duration_minutes: int = 0
    files_affected: List[str] = field(default_factory=list)
    project: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "category": self.category.value,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "files_affected": self.files_affected,
            "project": self.project,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JournalEvent":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            category=EventCategory(data["category"]),
            description=data["description"],
            duration_minutes=data.get("duration_minutes", 0),
            files_affected=data.get("files_affected", []),
            project=data.get("project"),
        )


@dataclass
class DailyJournal:
    """Represents a full day's journal entry."""
    date: str  # YYYY-MM-DD
    events: List[JournalEvent] = field(default_factory=list)
    summary: str = ""
    accomplishments: List[str] = field(default_factory=list)
    mistakes: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    hours_active: float = 0.0
    commits: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    outstanding_tasks: List[str] = field(default_factory=list)
    mood: str = "neutral"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "date": self.date,
            "events": [e.to_dict() for e in self.events],
            "summary": self.summary,
            "accomplishments": self.accomplishments,
            "mistakes": self.mistakes,
            "lessons_learned": self.lessons_learned,
            "hours_active": self.hours_active,
            "commits": self.commits,
            "files_modified": self.files_modified,
            "outstanding_tasks": self.outstanding_tasks,
            "mood": self.mood,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DailyJournal":
        """Create from dictionary."""
        return cls(
            date=data["date"],
            events=[JournalEvent.from_dict(e) for e in data.get("events", [])],
            summary=data.get("summary", ""),
            accomplishments=data.get("accomplishments", []),
            mistakes=data.get("mistakes", []),
            lessons_learned=data.get("lessons_learned", []),
            hours_active=data.get("hours_active", 0.0),
            commits=data.get("commits", []),
            files_modified=data.get("files_modified", []),
            outstanding_tasks=data.get("outstanding_tasks", []),
            mood=data.get("mood", "neutral"),
        )


@dataclass
class WeeklyReview:
    """Aggregated weekly review generated from daily journals."""
    week_start: str  # YYYY-MM-DD
    week_end: str  # YYYY-MM-DD
    accomplishments: List[str] = field(default_factory=list)
    mistakes: List[str] = field(default_factory=list)
    libraries_learned: List[str] = field(default_factory=list)
    projects_progressed: List[str] = field(default_factory=list)
    hours_spent: float = 0.0
    skills_improved: List[str] = field(default_factory=list)
    architecture_changes: List[str] = field(default_factory=list)
    goals_next_week: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "week_start": self.week_start,
            "week_end": self.week_end,
            "accomplishments": self.accomplishments,
            "mistakes": self.mistakes,
            "libraries_learned": self.libraries_learned,
            "projects_progressed": self.projects_progressed,
            "hours_spent": self.hours_spent,
            "skills_improved": self.skills_improved,
            "architecture_changes": self.architecture_changes,
            "goals_next_week": self.goals_next_week,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeeklyReview":
        """Create from dictionary."""
        return cls(
            week_start=data["week_start"],
            week_end=data["week_end"],
            accomplishments=data.get("accomplishments", []),
            mistakes=data.get("mistakes", []),
            libraries_learned=data.get("libraries_learned", []),
            projects_progressed=data.get("projects_progressed", []),
            hours_spent=data.get("hours_spent", 0.0),
            skills_improved=data.get("skills_improved", []),
            architecture_changes=data.get("architecture_changes", []),
            goals_next_week=data.get("goals_next_week", []),
            summary=data.get("summary", ""),
        )
