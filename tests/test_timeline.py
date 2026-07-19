"""Tests for JARVIS Timeline module (v5.4.0)."""

import sys
import os
import asyncio
import time
import tempfile
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.timeline.models import (
    TimelineEvent,
    TimelineEventType,
    TimelineQuery,
    TimelineSummary,
)
from jarvis.timeline.engine import TimelineEngine


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_event(title, event_type="custom", ts=0.0, date="", tags=None,
                related_entities=None, importance="useful", **kw):
    """Create a TimelineEvent with explicit timestamp for deterministic ordering."""
    ev = TimelineEvent(
        title=title,
        event_type=event_type,
        date=date,
        tags=tags or [],
        related_entities=related_entities or [],
        importance=importance,
        **kw,
    )
    if ts:
        ev.timestamp = ts
    return ev


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestTimelineModels:
    def test_event_custom_type(self):
        ev = TimelineEvent(title="Test Event", event_type="custom")
        assert ev.title == "Test Event"
        assert ev.event_type == "custom"
        assert ev.id.startswith("event_")
        assert ev.date != ""
        assert ev.timestamp > 0

    def test_event_project_created(self):
        ev = TimelineEvent(title="Started Jarvis v5", event_type="project_created")
        assert ev.event_type == "project_created"
        d = ev.to_dict()
        assert d["event_type"] == "project_created"
        assert d["title"] == "Started Jarvis v5"

    def test_event_milestone_type(self):
        ev = TimelineEvent(title="1.0 Release", event_type="milestone", importance="permanent")
        assert ev.event_type == "milestone"
        assert ev.importance == "permanent"

    def test_event_defaults_auto_id(self):
        a = TimelineEvent(title="A")
        b = TimelineEvent(title="B")
        assert a.id != b.id
        assert a.id.startswith("event_")
        assert len(a.id) > 6

    def test_event_defaults_auto_date(self):
        ev = TimelineEvent(title="Today")
        today = time.strftime("%Y-%m-%d")
        assert ev.date == today

    def test_event_defaults_auto_timestamp(self):
        before = time.time()
        ev = TimelineEvent(title="Now")
        after = time.time()
        assert before <= ev.timestamp <= after

    def test_event_to_dict(self):
        ev = TimelineEvent(
            title="Deploy",
            description="Deployed v5.4.0",
            event_type="project_updated",
            related_entities=["jarvis"],
            tags=["deploy", "release"],
            importance="important",
            metadata={"version": "5.4.0"},
        )
        d = ev.to_dict()
        assert d["title"] == "Deploy"
        assert d["description"] == "Deployed v5.4.0"
        assert d["related_entities"] == ["jarvis"]
        assert d["tags"] == ["deploy", "release"]
        assert d["importance"] == "important"
        assert d["metadata"]["version"] == "5.4.0"

    def test_event_explicit_values(self):
        ev = TimelineEvent(
            id="custom_1",
            title="T",
            event_type="lesson_learned",
            date="2025-06-15",
            timestamp=1000.0,
        )
        assert ev.id == "custom_1"
        assert ev.date == "2025-06-15"
        assert ev.timestamp == 1000.0

    def test_event_all_enum_types(self):
        for event_type in TimelineEventType:
            ev = TimelineEvent(title=f"Test {event_type.value}", event_type=event_type.value)
            assert ev.event_type == event_type.value

    def test_event_empty_related_and_tags(self):
        ev = TimelineEvent(title="X")
        assert ev.related_entities == []
        assert ev.tags == []
        assert ev.metadata == {}


class TestTimelineQuery:
    def test_query_defaults(self):
        q = TimelineQuery()
        assert q.start_date == ""
        assert q.end_date == ""
        assert q.event_types == []
        assert q.tags == []
        assert q.limit == 50

    def test_query_to_dict(self):
        q = TimelineQuery(
            start_date="2025-01-01",
            end_date="2025-12-31",
            event_types=["milestone", "project_created"],
            tags=["python"],
            related_entity="jarvis",
            min_importance="important",
            limit=10,
        )
        d = q.to_dict()
        assert d["start_date"] == "2025-01-01"
        assert d["end_date"] == "2025-12-31"
        assert d["event_types"] == ["milestone", "project_created"]
        assert d["tags"] == ["python"]
        assert d["related_entity"] == "jarvis"
        assert d["limit"] == 10


class TestTimelineSummary:
    def test_summary_defaults(self):
        s = TimelineSummary()
        assert s.total_events == 0
        assert s.date_range == ""
        assert s.event_type_counts == {}
        assert s.recent_events == []
        assert s.milestones == []

    def test_summary_to_dict(self):
        ev = TimelineEvent(title="M1", event_type="milestone")
        s = TimelineSummary(
            total_events=5,
            date_range="2025-01 — 2025-06",
            event_type_counts={"milestone": 2, "custom": 3},
            recent_events=[ev],
            milestones=[ev],
        )
        d = s.to_dict()
        assert d["total_events"] == 5
        assert d["recent_count"] == 1
        assert d["milestones_count"] == 1
        assert d["event_type_counts"]["milestone"] == 2


# ════════════════════════════════════════════════════════════
# Engine Tests
# ════════════════════════════════════════════════════════════

class TestTimelineEngine:
    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmp.close()
        self.engine = TimelineEngine(storage_path=self._tmp.name)

    def teardown_method(self):
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def _add_event_direct(self, event):
        """Insert a TimelineEvent directly into the engine's list."""
        self.engine._events.append(event)
        self.engine._sort_events()

    def test_add_event(self):
        ev = _run(self.engine.add_event("Test", "desc", "custom"))
        assert ev.title == "Test"
        assert ev.id.startswith("event_")

    def test_add_multiple_events(self):
        _run(self.engine.add_event("First", event_type="project_created"))
        _run(self.engine.add_event("Second", event_type="milestone"))
        _run(self.engine.add_event("Third", event_type="lesson_learned"))
        assert len(self.engine._events) == 3

    def test_get_event(self):
        ev = _run(self.engine.add_event("Find Me"))
        found = _run(self.engine.get_event(ev.id))
        assert found is not None
        assert found.title == "Find Me"

    def test_get_event_not_found(self):
        result = _run(self.engine.get_event("nonexistent"))
        assert result is None

    def test_query_by_type(self):
        _run(self.engine.add_event("A", event_type="milestone"))
        _run(self.engine.add_event("B", event_type="custom"))
        _run(self.engine.add_event("C", event_type="milestone"))
        q = TimelineQuery(event_types=["milestone"])
        results = _run(self.engine.query(q))
        assert len(results) == 2
        assert all(e.event_type == "milestone" for e in results)

    def test_query_by_tags(self):
        _run(self.engine.add_event("A", tags=["python"]))
        _run(self.engine.add_event("B", tags=["rust"]))
        _run(self.engine.add_event("C", tags=["python", "ml"]))
        q = TimelineQuery(tags=["python"])
        results = _run(self.engine.query(q))
        assert len(results) == 2

    def test_query_by_date_range(self):
        e1 = _make_event("Old", date="2024-01-01", ts=1000)
        e2 = _make_event("New", date="2025-06-15", ts=2000)
        self._add_event_direct(e1)
        self._add_event_direct(e2)
        self.engine._loaded = True
        q = TimelineQuery(start_date="2025-01-01", end_date="2025-12-31")
        results = _run(self.engine.query(q))
        assert len(results) == 1
        assert results[0].title == "New"

    def test_get_by_date(self):
        e1 = _make_event("Today", date="2025-07-10", ts=100)
        e2 = _make_event("Tomorrow", date="2025-07-11", ts=200)
        self._add_event_direct(e1)
        self._add_event_direct(e2)
        self.engine._loaded = True
        results = _run(self.engine.get_by_date("2025-07-10"))
        assert len(results) == 1
        assert results[0].title == "Today"

    def test_get_by_date_range(self):
        events = [
            _make_event("A", date="2025-01-01", ts=1),
            _make_event("B", date="2025-03-15", ts=2),
            _make_event("C", date="2025-06-01", ts=3),
            _make_event("D", date="2025-12-31", ts=4),
        ]
        for e in events:
            self._add_event_direct(e)
        self.engine._loaded = True
        results = _run(self.engine.get_by_date_range("2025-03-01", "2025-06-30"))
        assert len(results) == 2

    def test_get_by_type(self):
        _run(self.engine.add_event("A", event_type="milestone"))
        _run(self.engine.add_event("B", event_type="custom"))
        _run(self.engine.add_event("C", event_type="milestone"))
        results = _run(self.engine.get_by_type("milestone"))
        assert len(results) == 2

    def test_get_by_entity(self):
        _run(self.engine.add_event("A", related_entities=["jarvis", "python"]))
        _run(self.engine.add_event("B", related_entities=["rust"]))
        _run(self.engine.add_event("C", related_entities=["jarvis"]))
        results = _run(self.engine.get_by_entity("jarvis"))
        assert len(results) == 2

    def test_get_recent(self):
        events = [_make_event(f"E{i}", ts=float(100 + i)) for i in range(5)]
        for e in events:
            self._add_event_direct(e)
        self.engine._loaded = True
        recent = _run(self.engine.get_recent(3))
        assert len(recent) == 3
        assert recent[0].title == "E4"

    def test_get_milestones(self):
        _run(self.engine.add_event("M1", event_type="milestone"))
        _run(self.engine.add_event("N1", event_type="custom"))
        _run(self.engine.add_event("M2", event_type="milestone"))
        milestones = _run(self.engine.get_milestones())
        assert len(milestones) == 2

    def test_search(self):
        _run(self.engine.add_event("Python Setup", description="Configured python 3.12"))
        _run(self.engine.add_event("Rust Basics", tags=["rust"]))
        _run(self.engine.add_event("Python ML", tags=["python", "ml"]))
        results = _run(self.engine.search("python"))
        assert len(results) == 2

    def test_search_case_insensitive(self):
        _run(self.engine.add_event("JARVIS PROJECT", description="Building JARVIS v5"))
        results = _run(self.engine.search("jarvis"))
        assert len(results) == 1

    def test_get_summary(self):
        e1 = _make_event("A", event_type="milestone", date="2025-01-01", ts=1)
        e2 = _make_event("B", event_type="custom", date="2025-06-15", ts=2)
        self._add_event_direct(e1)
        self._add_event_direct(e2)
        self.engine._loaded = True
        summary = _run(self.engine.get_summary())
        assert summary.total_events == 2
        assert "milestone" in summary.event_type_counts
        assert len(summary.recent_events) == 2
        assert summary.date_range == "2025-01-01 — 2025-06-15"

    def test_get_summary_empty(self):
        summary = _run(self.engine.get_summary())
        assert summary.total_events == 0

    def test_what_happened_range(self):
        events = [
            _make_event("A", date="20250101", ts=1),
            _make_event("B", date="20250615", ts=2),
            _make_event("C", date="20251231", ts=3),
        ]
        for e in events:
            self._add_event_direct(e)
        self.engine._loaded = True
        result = _run(self.engine.what_happened("20250101 - 20250630"))
        assert "2 event" in result
        assert "A" in result
        assert "B" in result

    def test_what_happened_nothing(self):
        result = _run(self.engine.what_happened("2000-01-01"))
        assert "Nothing" in result

    def test_get_evolution(self):
        _run(self.engine.add_event("V1", related_entities=["project_x"]))
        _run(self.engine.add_event("V2", related_entities=["project_x", "other"]))
        _run(self.engine.add_event("V3", related_entities=["other"]))
        evo = _run(self.engine.get_evolution("project_x"))
        assert len(evo) == 2

    def test_save_and_load(self):
        _run(self.engine.add_event("Persistent", tags=["save_test"]))
        assert os.path.getsize(self._tmp.name) > 0

        engine2 = TimelineEngine(storage_path=self._tmp.name)
        _run(engine2._ensure_loaded())
        assert len(engine2._events) == 1
        assert engine2._events[0].title == "Persistent"

    def test_load_missing_file(self):
        engine = TimelineEngine(storage_path="/tmp/timeline_nonexistent_test.json")
        _run(engine._ensure_loaded())
        assert engine._events == []

    def test_query_min_importance(self):
        _run(self.engine.add_event("Low", importance="temporary"))
        _run(self.engine.add_event("Med", importance="useful"))
        _run(self.engine.add_event("High", importance="important"))
        _run(self.engine.add_event("Max", importance="permanent"))
        q = TimelineQuery(min_importance="important")
        results = _run(self.engine.query(q))
        assert len(results) == 2
        titles = [e.title for e in results]
        assert "High" in titles
        assert "Max" in titles

    def test_query_limit(self):
        events = [_make_event(f"E{i}", ts=float(i)) for i in range(20)]
        for e in events:
            self._add_event_direct(e)
        self.engine._loaded = True
        q = TimelineQuery(limit=5)
        results = _run(self.engine.query(q))
        assert len(results) == 5

    def test_events_sorted_by_timestamp_desc(self):
        e_old = _make_event("Old", ts=1000)
        e_new = _make_event("New", ts=2000)
        e_mid = _make_event("Mid", ts=1500)
        self._add_event_direct(e_old)
        self._add_event_direct(e_new)
        self._add_event_direct(e_mid)
        assert self.engine._events[0].title == "New"
        assert self.engine._events[1].title == "Mid"
        assert self.engine._events[2].title == "Old"

    def test_query_by_entity_and_type_combined(self):
        _run(self.engine.add_event("A", event_type="milestone", related_entities=["x"]))
        _run(self.engine.add_event("B", event_type="custom", related_entities=["x"]))
        _run(self.engine.add_event("C", event_type="milestone", related_entities=["y"]))
        q = TimelineQuery(event_types=["milestone"], related_entity="x")
        results = _run(self.engine.query(q))
        assert len(results) == 1
        assert results[0].title == "A"

    def test_add_event_persists(self):
        _run(self.engine.add_event("Persisted"))
        with open(self._tmp.name, "r") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["title"] == "Persisted"

    def test_search_by_tag(self):
        _run(self.engine.add_event("A", tags=["important", "deploy"]))
        _run(self.engine.add_event("B", tags=["note"]))
        results = _run(self.engine.search("deploy"))
        assert len(results) == 1

    def test_get_by_entity_empty(self):
        results = _run(self.engine.get_by_entity("nonexistent"))
        assert results == []
