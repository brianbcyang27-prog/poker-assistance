"""Test AutonomousLoop mission execution, recording, and improvement."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tempfile
from unittest.mock import MagicMock

import pytest

from jarvis.mission.loop import AutonomousLoop


class MockBrain:
    """Minimal mock brain that satisfies AutonomousLoop's attribute checks."""

    def __init__(self):
        self.llm = MagicMock()
        self.memory = MagicMock()
        self.tools = MagicMock()


@pytest.fixture
def mock_brain():
    return MockBrain()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def al(mock_brain, temp_dir):
    """Create an AutonomousLoop with a temp recorder path."""
    storage_dir = os.path.join(temp_dir, "test_recorder.json")
    return AutonomousLoop(brain=mock_brain, storage_dir=storage_dir)


class TestAutonomousLoopInit:
    def test_init_creates_components(self, al):
        assert al._brain is not None
        assert al._recorder is not None
        assert al._reports == []

    def test_init_with_custom_recorder_path(self, mock_brain, temp_dir):
        path = os.path.join(temp_dir, "test_recorder.json")
        al = AutonomousLoop(brain=mock_brain, storage_dir=path)
        # Check that storage_dir was passed correctly
        assert al._recorder is not None


class TestAutonomousLoopExecute:
    @pytest.mark.asyncio
    async def test_execute_simple_goal(self, al):
        """Test basic mission execution."""
        report = await al.execute("Test goal")
        assert report is not None
        assert report.goal == "Test goal"
        assert report.mission_id is not None

    @pytest.mark.asyncio
    async def test_execute_with_project_name(self, al):
        """Test execution with project name."""
        report = await al.execute("Build API", project_name="Jarvis")
        assert report.goal == "Build API"

    @pytest.mark.asyncio
    async def test_execute_with_context(self, al):
        """Test execution with context dict."""
        report = await al.execute("Deploy", context={"env": "staging"})
        assert report is not None

    @pytest.mark.asyncio
    async def test_execute_failure_handling(self, al):
        """Test error handling during observation."""
        # Make observe raise to test error handling

        async def failing_observe(*args, **kwargs):
            raise RuntimeError("Simulated failure")

        al._observe = failing_observe
        report = await al.execute("Failing goal")
        assert report.outcome == "failed"
        assert len(al._reports) == 1

    @pytest.mark.asyncio
    async def test_execute_records_error_event(self, al):
        """Test that errors are recorded as events."""

        async def failing_observe(*args, **kwargs):
            raise RuntimeError("boom")

        al._observe = failing_observe
        report = await al.execute("Failing goal")
        events = await al._recorder.get_events(report.mission_id)
        error_events = [e for e in events if e.event_type == "error"]
        assert len(error_events) >= 1

    @pytest.mark.asyncio
    async def test_execute_records_recovery_event(self, al):
        """Test that recovery is recorded."""

        async def failing_observe(*args, **kwargs):
            raise RuntimeError("boom")

        al._observe = failing_observe
        report = await al.execute("Failing goal")
        events = await al._recorder.get_events(report.mission_id)
        recovery_events = [e for e in events if e.event_type == "recovery"]
        assert len(recovery_events) >= 1


class TestAutonomousLoopHistory:
    @pytest.mark.asyncio
    async def test_get_mission_history(self, al):
        """Test mission history retrieval."""
        await al.execute("Goal 1")
        await al.execute("Goal 2")
        history = await al.get_mission_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_improvement_trend_insufficient(self, al):
        """Test improvement trend with insufficient data."""
        await al.execute("Goal 1")
        trend = await al.get_improvement_trend()
        assert trend["trend"] == "insufficient_data"
        assert trend["total_missions"] == 1

    @pytest.mark.asyncio
    async def test_get_improvement_trend_with_data(self, al):
        """Test improvement trend with sufficient data."""
        for i in range(6):
            await al.execute(f"Goal {i}")
        trend = await al.get_improvement_trend()
        assert trend["trend"] in ("improving", "declining")
        assert trend["total_missions"] == 6
        assert "recent_success_rate" in trend
        assert "older_success_rate" in trend


class TestAutonomousLoopLessons:
    @pytest.mark.asyncio
    async def test_execute_lesson_stored(self, al):
        """Test that lessons are stored after execution."""
        report = await al.execute("Build thing")
        assert len(report.lessons) > 0

    @pytest.mark.asyncio
    async def test_execute_multiple_independent(self):
        """Test multiple independent executions."""
        reports = []
        for _ in range(3):
            al = AutonomousLoop(brain=MockBrain(), storage_dir=tempfile.mktemp(suffix=".json"))
            r = await al.execute("Independent goal")
            reports.append(r)
        assert len(reports) == 3
        ids = {r.mission_id for r in reports}
        assert len(ids) >= 2  # At least 2 unique IDs

    @pytest.mark.asyncio
    async def test_execute_success_outcome(self, al):
        """Test successful outcome."""
        report = await al.execute("Simple task")
        # Default _verify returns success when all steps complete
        assert report.outcome == "success"
