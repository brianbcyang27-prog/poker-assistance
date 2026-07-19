"""Timeline engine — stores and queries personal events chronologically."""
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import TimelineEvent, TimelineQuery, TimelineSummary

logger = logging.getLogger(__name__)

MEMORY_STORE = os.path.join("memory_store", "timeline.json")

# Importance ranking for sorting and filtering
_IMPORTANCE_ORDER = {"temporary": 0, "useful": 1, "important": 2, "permanent": 3}


class TimelineEngine:
    """Chronological event store with natural-language queries."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._storage_path = storage_path or MEMORY_STORE
        self._events: List[TimelineEvent] = []
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def add_event(
        self,
        title: str,
        description: str = "",
        event_type: str = "custom",
        date: str = "",
        related_entities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        importance: str = "useful",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TimelineEvent:
        """Create and store a new timeline event."""
        event = TimelineEvent(
            title=title,
            description=description,
            event_type=event_type,
            date=date,
            related_entities=related_entities or [],
            tags=tags or [],
            importance=importance,
            metadata=metadata or {},
        )
        self._events.append(event)
        self._sort_events()
        await self.save()
        logger.info("Added event: %s (%s)", event.title, event.id)
        return event

    async def get_event(self, event_id: str) -> Optional[TimelineEvent]:
        """Retrieve a single event by ID."""
        for ev in self._events:
            if ev.id == event_id:
                return ev
        return None

    async def query(self, q: TimelineQuery) -> List[TimelineEvent]:
        """Run a structured query against the timeline."""
        await self._ensure_loaded()
        results = list(self._events)

        if q.start_date:
            results = [e for e in results if e.date >= q.start_date]
        if q.end_date:
            results = [e for e in results if e.date <= q.end_date]
        if q.event_types:
            results = [e for e in results if e.event_type in q.event_types]
        if q.tags:
            results = [
                e for e in results if any(t in e.tags for t in q.tags)
            ]
        if q.related_entity:
            results = [
                e for e in results if q.related_entity in e.related_entities
            ]
        if q.min_importance:
            min_ord = _IMPORTANCE_ORDER.get(q.min_importance, 0)
            results = [
                e for e in results
                if _IMPORTANCE_ORDER.get(e.importance, 0) >= min_ord
            ]
        return results[: q.limit]

    async def get_by_date(self, date: str) -> List[TimelineEvent]:
        """Get all events on a specific date (YYYY-MM-DD)."""
        await self._ensure_loaded()
        return [e for e in self._events if e.date == date]

    async def get_by_date_range(
        self, start_date: str, end_date: str
    ) -> List[TimelineEvent]:
        """Get events within a date range (inclusive)."""
        await self._ensure_loaded()
        return [
            e for e in self._events
            if start_date <= e.date <= end_date
        ]

    async def get_by_type(self, event_type: str) -> List[TimelineEvent]:
        """Get all events of a given type."""
        await self._ensure_loaded()
        return [e for e in self._events if e.event_type == event_type]

    async def get_by_entity(self, entity_id: str) -> List[TimelineEvent]:
        """Get all events related to a specific entity."""
        await self._ensure_loaded()
        return [
            e for e in self._events if entity_id in e.related_entities
        ]

    async def get_recent(self, n: int = 10) -> List[TimelineEvent]:
        """Get the N most recent events."""
        await self._ensure_loaded()
        return self._events[:n]

    async def get_milestones(self) -> List[TimelineEvent]:
        """Get all milestone events, newest first."""
        await self._ensure_loaded()
        return [e for e in self._events if e.event_type == "milestone"]

    async def search(self, query: str) -> List[TimelineEvent]:
        """Free-text search across title, description, and tags."""
        await self._ensure_loaded()
        q = query.lower()
        return [
            e for e in self._events
            if q in e.title.lower()
            or q in e.description.lower()
            or any(q in t.lower() for t in e.tags)
        ]

    async def get_summary(self) -> TimelineSummary:
        """Build a summary of the entire timeline."""
        await self._ensure_loaded()
        if not self._events:
            return TimelineSummary()

        type_counts: Dict[str, int] = defaultdict(int)
        for ev in self._events:
            type_counts[ev.event_type] += 1

        earliest = self._events[-1].date if self._events else ""
        latest = self._events[0].date if self._events else ""
        date_range = f"{earliest} — {latest}" if earliest != latest else earliest

        return TimelineSummary(
            total_events=len(self._events),
            date_range=date_range,
            event_type_counts=dict(type_counts),
            recent_events=self._events[:10],
            milestones=[e for e in self._events if e.event_type == "milestone"],
        )

    async def what_happened(self, date_or_range: str) -> str:
        """Answer 'what happened on X?' in natural language.

        Accepts a single date (YYYY-MM-DD) or a range ("2025-01 — 2025-03").
        """
        await self._ensure_loaded()
        parts = date_or_range.replace("—", "-").replace("–", "-").split("-")
        clean = [p.strip() for p in parts if p.strip()]

        if len(clean) == 1:
            events = [e for e in self._events if e.date == clean[0]]
            label = clean[0]
        elif len(clean) >= 2:
            start = clean[0]
            end = clean[1] if len(clean) > 1 else clean[0]
            events = [e for e in self._events if start <= e.date <= end]
            label = f"{start} to {end}"
        else:
            return f"No events found for '{date_or_range}'."

        if not events:
            return f"Nothing recorded for {label}."

        lines = [f"On {label}, {len(events)} event(s) occurred:"]
        for ev in events[:15]:
            lines.append(f"  - [{ev.event_type}] {ev.title}")
        if len(events) > 15:
            lines.append(f"  ... and {len(events) - 15} more.")
        return "\n".join(lines)

    async def get_evolution(self, entity_id: str) -> List[TimelineEvent]:
        """Track how something evolved over time."""
        await self._ensure_loaded()
        return [
            e for e in self._events if entity_id in e.related_entities
        ]

    async def save(self) -> None:
        """Persist events to disk."""
        os.makedirs(os.path.dirname(self._storage_path) or ".", exist_ok=True)
        data = [e.to_dict() for e in self._events]
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug("Saved %d events", len(self._events))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load(self) -> None:
        """Load events from disk."""
        if not os.path.exists(self._storage_path):
            self._events = []
            self._loaded = True
            return
        try:
            with open(self._storage_path, "r") as f:
                data = json.load(f)
            self._events = [TimelineEvent(**item) for item in data]
            self._sort_events()
            logger.info("Loaded %d events", len(self._events))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load timeline: %s", exc)
            self._events = []
        self._loaded = True

    async def _ensure_loaded(self) -> None:
        if not self._loaded:
            await self._load()

    def _sort_events(self) -> None:
        """Sort events by timestamp descending (newest first)."""
        self._events.sort(key=lambda e: e.timestamp, reverse=True)
