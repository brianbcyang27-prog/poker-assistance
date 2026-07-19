import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import tempfile
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from jarvis.mission.loop import AutonomousLoop


loop = asyncio.get_event_loop()


class MockBrain:
    """Minimal mock brain that satisfies AutonomousLoop's attribute checks."""

    def __init__(self):
        self.context_manager = None
        self.memory_manager = None
        self.reasoning_engine = None


class TestAutonomousLoop:
    def _make(self):
        tmpdir = tempfile.mkdtemp()
        brain = MockBrain()
        auto_loop = AutonomousLoop(brain, storage_dir=tmpdir)
        return auto_loop

    def test_create(self):
        al = self._make()
        assert al._brain is not None
        assert al._recorder is not None
        assert al._reports == []

    def test_recorder_exposed(self):
        al = self._make()
        assert al.recorder is not None

    def test_execute_simple_goal(self):
        al = self._make()
        report = loop.run_until_complete(al.execute("Build a simple calculator"))
        assert report is not None
        assert report.mission_id.startswith("auto_")
        assert report.outcome in ("success", "partial", "failed")
        assert report.total_events > 0
        assert report.duration_seconds >= 0

    def test_execute_creates_report(self):
        al = self._make()
        assert len(al._reports) == 0
        loop.run_until_complete(al.execute("Test goal"))
        assert len(al._reports) == 1

    def test_execute_records_events(self):
        al = self._make()
        report = loop.run_until_complete(al.execute("Build app"))
        events = loop.run_until_complete(al._recorder.get_events(report.mission_id))
        event_titles = [e.title for e in events]
        assert "Observe" in event_titles
        assert "Understand" in event_titles
        assert "Plan" in event_titles
        assert "Act" in event_titles
        assert "Verify" in event_titles
        assert "Reflect" in event_titles
        assert "Remember" in event_titles
        assert "Improve" in event_titles

    def test_execute_with_project_name(self):
        al = self._make()
        report = loop.run_until_complete(
            al.execute("Build API", project_name="Jarvis")
        )
        assert report.goal == "Build API"

    def test_execute_with_context(self):
        al = self._make()
        report = loop.run_until_complete(
            al.execute("Deploy", context={"env": "staging"})
        )
        assert report is not None

    def test_execute_failure_handling(self):
        al = self._make()
        # Make observe raise to test error handling
        original_observe = al._observe

        async def failing_observe(*args, **kwargs):
            raise RuntimeError("Simulated failure")

        al._observe = failing_observe
        report = loop.run_until_complete(al.execute("Failing goal"))
        assert report.outcome == "failed"
        assert len(al._reports) == 1

    def test_execute_records_error_event(self):
        al = self._make()

        async def failing_observe(*args, **kwargs):
            raise RuntimeError("boom")

        al._observe = failing_observe
        report = loop.run_until_complete(al.execute("Failing goal"))
        events = loop.run_until_complete(al._recorder.get_events(report.mission_id))
        error_events = [e for e in events if e.event_type == "error"]
        assert len(error_events) >= 1

    def test_execute_records_recovery_event(self):
        al = self._make()

        async def failing_observe(*args, **kwargs):
            raise RuntimeError("boom")

        al._observe = failing_observe
        report = loop.run_until_complete(al.execute("Failing goal"))
        events = loop.run_until_complete(al._recorder.get_events(report.mission_id))
        recovery_events = [e for e in events if e.event_type == "recovery"]
        assert len(recovery_events) >= 1

    def test_get_mission_history(self):
        al = self._make()
        loop.run_until_complete(al.execute("Goal 1"))
        loop.run_until_complete(al.execute("Goal 2"))
        history = loop.run_until_complete(al.get_mission_history())
        assert len(history) == 2

    def test_get_improvement_trend_insufficient(self):
        al = self._make()
        loop.run_until_complete(al.execute("Goal 1"))
        trend = loop.run_until_complete(al.get_improvement_trend())
        assert trend["trend"] == "insufficient_data"
        assert trend["total_missions"] == 1

    def test_get_improvement_trend_with_data(self):
        al = self._make()
        for i in range(6):
            loop.run_until_complete(al.execute(f"Goal {i}"))
        trend = loop.run_until_complete(al.get_improvement_trend())
        assert trend["trend"] in ("improving", "declining")
        assert trend["total_missions"] == 6
        assert "recent_success_rate" in trend
        assert "older_success_rate" in trend

    def test_execute_lesson_stored(self):
        al = self._make()
        report = loop.run_until_complete(al.execute("Build thing"))
        assert len(report.lessons) > 0

    def test_execute_multiple_independent(self):
        reports = []
        for _ in range(3):
            al = self._make()
            r = loop.run_until_complete(al.execute("Independent goal"))
            reports.append(r)
        assert len(reports) == 3
        ids = {r.mission_id for r in reports}
        assert len(ids) == 3

    def test_execute_success_outcome(self):
        al = self._make()
        report = loop.run_until_complete(al.execute("Simple task"))
        # Default _verify returns success when all steps complete
        assert report.outcome == "success"
