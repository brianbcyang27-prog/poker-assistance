import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import tempfile
import time
import pytest

from jarvis.mission.replay.models import MissionEvent, MissionReport, MissionReplayQuery, MissionEventType
from jarvis.mission.replay.recorder import MissionRecorder
from jarvis.mission.replay.replay import MissionReplay


loop = asyncio.get_event_loop()


# ── MissionEvent ──────────────────────────────────────────────────────────────

class TestMissionEvent:
    def test_create_default(self):
        e = MissionEvent()
        assert e.id.startswith("evt_")
        assert e.timestamp > 0
        assert e.success is True
        assert e.duration_ms == 0

    def test_create_explicit(self):
        e = MissionEvent(
            mission_id="m1",
            event_type="action",
            title="Create files",
            description="Wrote 5 modules",
            agent_id="architect",
        )
        assert e.mission_id == "m1"
        assert e.title == "Create files"
        assert e.agent_id == "architect"

    def test_to_dict(self):
        e = MissionEvent(mission_id="m1", event_type="error", title="fail", success=False)
        d = e.to_dict()
        assert d["mission_id"] == "m1"
        assert d["event_type"] == "error"
        assert d["success"] is False
        assert "id" in d
        assert "timestamp" in d
        assert "metadata" in d

    def test_unique_ids(self):
        a = MissionEvent()
        b = MissionEvent()
        assert a.id != b.id

    def test_preserves_explicit_id(self):
        e = MissionEvent(id="custom_evt")
        assert e.id == "custom_evt"

    def test_metadata_default(self):
        e = MissionEvent()
        assert e.metadata == {}

    def test_metadata_populated(self):
        e = MissionEvent(metadata={"key": "value", "count": 5})
        d = e.to_dict()
        assert d["metadata"]["key"] == "value"
        assert d["metadata"]["count"] == 5


# ── MissionReport ─────────────────────────────────────────────────────────────

class TestMissionReport:
    def test_create_default(self):
        r = MissionReport()
        assert r.mission_id == ""
        assert r.outcome == ""
        assert r.total_events == 0

    def test_create_with_data(self):
        r = MissionReport(
            mission_id="m1",
            goal="build app",
            outcome="success",
            duration_seconds=42.5,
            total_events=10,
        )
        assert r.mission_id == "m1"
        assert r.outcome == "success"
        assert r.duration_seconds == 42.5

    def test_to_dict(self):
        r = MissionReport(mission_id="m1", goal="test", outcome="success")
        d = r.to_dict()
        assert d["mission_id"] == "m1"
        assert d["goal"] == "test"
        assert "actions" in d
        assert "problems" in d
        assert "lessons" in d
        assert "duration_seconds" in d

    def test_to_dict_with_events(self):
        evt = MissionEvent(title="action1", event_type="action")
        prob = MissionEvent(title="error1", event_type="error")
        r = MissionReport(actions=[evt], problems=[prob])
        d = r.to_dict()
        assert len(d["actions"]) == 1
        assert len(d["problems"]) == 1

    def test_to_timeline(self):
        evt1 = MissionEvent(title="start", event_type="started", timestamp=1000.0)
        evt2 = MissionEvent(title="action", event_type="action", timestamp=2000.0)
        r = MissionReport(actions=[evt1, evt2])
        timeline = r.to_timeline()
        assert len(timeline) == 2
        assert timeline[0]["title"] == "start"
        assert timeline[0]["time"] is not None
        assert "type" in timeline[0]

    def test_to_timeline_sorted(self):
        evt1 = MissionEvent(title="later", timestamp=3000.0)
        evt2 = MissionEvent(title="earlier", timestamp=1000.0)
        r = MissionReport(actions=[evt1, evt2])
        timeline = r.to_timeline()
        assert timeline[0]["title"] == "earlier"
        assert timeline[1]["title"] == "later"

    def test_to_timeline_mixed(self):
        evt = MissionEvent(title="act", event_type="action", timestamp=1000.0)
        prob = MissionEvent(title="err", event_type="error", timestamp=2000.0)
        r = MissionReport(actions=[evt], problems=[prob])
        timeline = r.to_timeline()
        assert len(timeline) == 2


# ── MissionReplayQuery ────────────────────────────────────────────────────────

class TestMissionReplayQuery:
    def test_create_default(self):
        q = MissionReplayQuery()
        assert q.mission_id == ""
        assert q.limit == 100

    def test_to_dict(self):
        q = MissionReplayQuery(mission_id="m1", limit=50)
        d = q.to_dict()
        assert d["mission_id"] == "m1"
        assert d["limit"] == 50
        assert "event_types" in d


# ── MissionRecorder ───────────────────────────────────────────────────────────

class TestMissionRecorder:
    def _make(self):
        tmpdir = tempfile.mkdtemp()
        return MissionRecorder(storage_dir=tmpdir)

    def test_create(self):
        rec = self._make()
        assert rec._events == {}

    def test_start_recording(self):
        rec = self._make()
        event = loop.run_until_complete(
            rec.start_recording("m1", "Build chat app")
        )
        assert event.event_type == "started"
        assert event.mission_id == "m1"
        assert "Build chat app" in event.description

    def test_record_event(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        event = loop.run_until_complete(
            rec.record_event("m1", "action", "Created files", description="wrote 5 modules")
        )
        assert event.title == "Created files"
        assert event.event_type == "action"

    def test_record_error(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        event = loop.run_until_complete(
            rec.record_error("m1", "ImportError", "missing module")
        )
        assert event.event_type == "error"
        assert event.success is False

    def test_record_recovery(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        event = loop.run_until_complete(
            rec.record_recovery("m1", "Installed missing package")
        )
        assert event.event_type == "recovery"
        assert event.success is True

    def test_complete(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "Build app"))
        loop.run_until_complete(rec.record_event("m1", "action", "step1"))
        report = loop.run_until_complete(
            rec.complete("m1", "success", "All tests pass", ["Use async"])
        )
        assert report.mission_id == "m1"
        assert report.outcome == "success"
        assert report.verification == "All tests pass"
        assert "Use async" in report.lessons
        assert report.total_events >= 2

    def test_get_events(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        loop.run_until_complete(rec.record_event("m1", "action", "step"))
        events = loop.run_until_complete(rec.get_events("m1"))
        assert len(events) == 2  # start + step

    def test_get_report(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        loop.run_until_complete(rec.complete("m1", "success"))
        report = loop.run_until_complete(rec.get_report("m1"))
        assert report is not None
        assert report.outcome == "success"

    def test_get_report_nonexistent(self):
        rec = self._make()
        report = loop.run_until_complete(rec.get_report("nope"))
        assert report is None

    def test_list_missions(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal1"))
        loop.run_until_complete(rec.complete("m1", "success"))
        loop.run_until_complete(rec.start_recording("m2", "goal2"))
        loop.run_until_complete(rec.complete("m2", "failed"))
        missions = loop.run_until_complete(rec.list_missions())
        assert len(missions) == 2

    def test_list_missions_limit(self):
        rec = self._make()
        for i in range(5):
            mid = f"m{i}"
            loop.run_until_complete(rec.start_recording(mid, f"goal{i}"))
            loop.run_until_complete(rec.complete(mid, "success"))
        missions = loop.run_until_complete(rec.list_missions(limit=2))
        assert len(missions) == 2

    def test_persists_to_disk(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        loop.run_until_complete(rec.record_event("m1", "action", "step"))
        loop.run_until_complete(rec.complete("m1", "success"))

        # Load from disk
        rec2 = MissionRecorder(storage_dir=rec._storage)
        events = loop.run_until_complete(rec2.get_events("m1"))
        assert len(events) >= 2

    def test_report_failed_outcome(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        report = loop.run_until_complete(rec.complete("m1", "failed", "timeout"))
        assert report.outcome == "failed"

    def test_multiple_events(self):
        rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        for i in range(5):
            loop.run_until_complete(rec.record_event("m1", "action", f"step{i}"))
        events = loop.run_until_complete(rec.get_events("m1"))
        assert len(events) == 6  # start + 5 steps


# ── MissionReplay ─────────────────────────────────────────────────────────────

class TestMissionReplay:
    def _make(self):
        tmpdir = tempfile.mkdtemp()
        rec = MissionRecorder(storage_dir=tmpdir)
        return MissionReplay(recorder=rec), rec

    def _populate(self):
        replay, rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "Build app"))
        loop.run_until_complete(rec.record_event("m1", "action", "Step 1"))
        loop.run_until_complete(rec.record_event("m1", "action", "Step 2"))
        loop.run_until_complete(rec.complete("m1", "success", "All good", ["Use async"]))
        return replay

    def test_create(self):
        replay, _ = self._make()
        assert replay._recorder is not None

    def test_get_timeline(self):
        replay = self._populate()
        timeline = loop.run_until_complete(replay.get_timeline("m1"))
        assert len(timeline) >= 2
        assert all("title" in t for t in timeline)

    def test_get_timeline_nonexistent(self):
        replay, _ = self._make()
        timeline = loop.run_until_complete(replay.get_timeline("nope"))
        assert timeline == []

    def test_get_report(self):
        replay = self._populate()
        report = loop.run_until_complete(replay.get_report("m1"))
        assert report is not None
        assert report.outcome == "success"

    def test_get_summary(self):
        replay = self._populate()
        summary = loop.run_until_complete(replay.get_summary("m1"))
        assert "m1" in summary
        assert "success" in summary
        assert "Build app" in summary

    def test_get_summary_nonexistent(self):
        replay, _ = self._make()
        summary = loop.run_until_complete(replay.get_summary("nope"))
        assert "no data" in summary

    def test_get_lessons(self):
        replay = self._populate()
        lessons = loop.run_until_complete(replay.get_lessons("m1"))
        assert "Use async" in lessons

    def test_get_lessons_nonexistent(self):
        replay, _ = self._make()
        lessons = loop.run_until_complete(replay.get_lessons("nope"))
        assert lessons == []

    def test_get_stats(self):
        replay = self._populate()
        stats = loop.run_until_complete(replay.get_stats())
        assert stats["total"] == 1
        assert stats["success"] == 1
        assert stats["success_rate"] == 1.0

    def test_get_stats_empty(self):
        replay, _ = self._make()
        stats = loop.run_until_complete(replay.get_stats())
        assert stats["total"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_failed_missions(self):
        replay, rec = self._make()
        loop.run_until_complete(rec.start_recording("m1", "goal"))
        loop.run_until_complete(rec.complete("m1", "success"))
        loop.run_until_complete(rec.start_recording("m2", "goal"))
        loop.run_until_complete(rec.complete("m2", "failed"))
        failed = loop.run_until_complete(replay.get_failed_missions())
        assert len(failed) == 1
        assert failed[0]["mission_id"] == "m2"
