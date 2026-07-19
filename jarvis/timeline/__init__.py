"""Personal Timeline — chronological record of projects, decisions, and growth.

Maintains a sorted timeline of significant events with natural language
queries ("what happened last month?") and entity evolution tracking.

Usage:
    engine = TimelineEngine()
    await engine.add_event("Started Jarvis v5", "Began the rewrite", "project_created")
    events = await engine.get_recent(10)
    summary = await engine.get_summary()
"""

from .models import (
    TimelineEvent,
    TimelineEventType,
    TimelineQuery,
    TimelineSummary,
)

__all__ = [
    "TimelineEvent",
    "TimelineEventType",
    "TimelineQuery",
    "TimelineSummary",
]
