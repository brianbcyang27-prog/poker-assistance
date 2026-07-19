import sys
import os
import asyncio
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from jarvis.brain.living_models import (
    ActionResult,
    ContextSnapshot,
    PlannedAction,
    Prediction,
    Understanding,
)
from jarvis.brain.loop import LivingBrain


# ---------------------------------------------------------------------------
# LivingBrainModels
# ---------------------------------------------------------------------------


class TestLivingBrainModels:
    def test_context_snapshot_defaults(self):
        snap = ContextSnapshot()
        assert isinstance(snap.timestamp, float)
        assert snap.active_app == ""
        assert snap.active_file == ""
        assert snap.git_branch == ""
        assert snap.browser_tabs == []
        assert snap.open_files == []
        assert snap.running_terminals == []
        assert snap.current_mission == ""
        assert snap.cpu_percent == 0.0
        assert snap.memory_percent == 0.0
        assert snap.context_dict == {}

    def test_context_snapshot_custom(self):
        snap = ContextSnapshot(
            active_app="VSCode",
            active_file="/tmp/main.py",
            git_branch="main",
            browser_tabs=["https://example.com"],
            open_files=["a.py", "b.py"],
            running_terminals=["zsh"],
            current_mission="testing",
            cpu_percent=42.5,
            memory_percent=67.3,
            context_dict={"key": "val"},
        )
        assert snap.active_app == "VSCode"
        assert len(snap.browser_tabs) == 1
        assert snap.cpu_percent == 42.5

    def test_understanding_defaults(self):
        u = Understanding()
        assert isinstance(u.snapshot, ContextSnapshot)
        assert u.summary == ""
        assert u.detected_patterns == []
        assert u.anomalies == []
        assert u.context_changes == []

    def test_understanding_custom(self):
        snap = ContextSnapshot(active_app="Terminal")
        u = Understanding(snapshot=snap, summary="Working in terminal", detected_patterns=["coding"])
        assert u.snapshot.active_app == "Terminal"
        assert "coding" in u.detected_patterns

    def test_prediction_defaults(self):
        p = Prediction()
        assert p.description == ""
        assert p.confidence == 0.0
        assert p.category == "work"
        assert p.timeframe == "immediate"

    def test_prediction_custom(self):
        p = Prediction(description="User needs help", confidence=0.8, category="assist", timeframe="5min")
        assert p.confidence == 0.8
        assert p.category == "assist"

    def test_planned_action_defaults(self):
        a = PlannedAction()
        assert a.action_type == "suggest"
        assert a.description == ""
        assert a.priority == 0
        assert a.auto_approve is False
        assert a.confidence == 0.0

    def test_planned_action_custom(self):
        a = PlannedAction(action_type="notify", description="Remind to commit", priority=5, auto_approve=True)
        assert a.auto_approve is True
        assert a.priority == 5

    def test_action_result_defaults(self):
        r = ActionResult()
        assert isinstance(r.action, PlannedAction)
        assert r.executed is False
        assert r.result == ""
        assert isinstance(r.timestamp, float)

    def test_action_result_custom(self):
        action = PlannedAction(description="test")
        r = ActionResult(action=action, executed=True, result="done")
        assert r.executed is True
        assert r.action.description == "test"


# ---------------------------------------------------------------------------
# LivingBrain
# ---------------------------------------------------------------------------


class TestLivingBrain:
    @pytest.fixture
    def brain(self):
        return LivingBrain(interval_seconds=60.0)

    def test_init_defaults(self):
        b = LivingBrain()
        status = b.get_status()
        assert status["running"] is False
        assert status["ticks"] == 0
        assert status["interval_seconds"] == 30.0
        assert status["timeline_size"] == 0

    def test_init_custom_interval(self, brain):
        assert brain._interval == 60.0

    def test_observe(self, brain):
        snap = asyncio.get_event_loop().run_until_complete(brain.observe())
        assert isinstance(snap, ContextSnapshot)
        assert "tick" in snap.context_dict
        assert snap.context_dict["tick"] == 0

    def test_understand(self, brain):
        snap = ContextSnapshot()
        understanding = asyncio.get_event_loop().run_until_complete(brain.understand(snap))
        assert isinstance(understanding, Understanding)
        assert understanding.snapshot is snap
        assert "Context captured" in understanding.summary

    def test_predict(self, brain):
        understanding = Understanding()
        predictions = asyncio.get_event_loop().run_until_complete(brain.predict(understanding))
        assert isinstance(predictions, list)

    def test_plan(self, brain):
        predictions = [Prediction(description="test", confidence=0.5)]
        actions = asyncio.get_event_loop().run_until_complete(brain.plan(predictions))
        assert isinstance(actions, list)

    def test_assist_empty(self, brain):
        results = asyncio.get_event_loop().run_until_complete(brain.assist([]))
        assert results == []

    def test_assist_auto_approve(self, brain):
        action = PlannedAction(description="test", auto_approve=True)
        results = asyncio.get_event_loop().run_until_complete(brain.assist([action]))
        assert len(results) == 1
        assert results[0].executed is True
        assert "Auto-approved" in results[0].result

    def test_assist_no_auto_approve(self, brain):
        action = PlannedAction(description="test", auto_approve=False)
        results = asyncio.get_event_loop().run_until_complete(brain.assist([action]))
        assert len(results) == 1
        assert results[0].executed is False
        assert "approval" in results[0].result.lower()

    def test_tick_single_iteration(self, brain):
        asyncio.get_event_loop().run_until_complete(brain.tick())
        status = brain.get_status()
        assert status["ticks"] == 1
        assert status["last_tick"] is not None
        assert status["timeline_size"] == 1

    def test_get_status(self, brain):
        status = brain.get_status()
        assert "running" in status
        assert "ticks" in status
        assert "last_tick" in status
        assert "interval_seconds" in status
        assert "uptime_seconds" in status
        assert "timeline_size" in status

    def test_get_timeline(self, brain):
        timeline = brain.get_timeline()
        assert isinstance(timeline, list)
        assert len(timeline) == 0

    def test_get_timeline_after_tick(self, brain):
        asyncio.get_event_loop().run_until_complete(brain.tick())
        timeline = brain.get_timeline()
        assert len(timeline) == 1
        assert isinstance(timeline[0], ContextSnapshot)

    def test_multiple_ticks(self, brain):
        for _ in range(5):
            asyncio.get_event_loop().run_until_complete(brain.tick())
        status = brain.get_status()
        assert status["ticks"] == 5
        assert status["timeline_size"] == 5

    def test_start_and_stop(self, brain):
        asyncio.get_event_loop().run_until_complete(brain.start())
        assert brain._running is True
        assert brain._task is not None
        assert brain._start_time is not None
        asyncio.get_event_loop().run_until_complete(brain.stop())
        assert brain._running is False
        assert brain._task is None

    def test_stop_when_not_running(self, brain):
        asyncio.get_event_loop().run_until_complete(brain.stop())
        assert brain._running is False

    def test_start_when_already_running(self, brain):
        asyncio.get_event_loop().run_until_complete(brain.start())
        asyncio.get_event_loop().run_until_complete(brain.start())
        assert brain._running is True
        asyncio.get_event_loop().run_until_complete(brain.stop())

    def test_timeline_maxlen(self, brain):
        brain2 = LivingBrain(interval_seconds=1.0)
        for _ in range(105):
            asyncio.get_event_loop().run_until_complete(brain2.tick())
        assert len(brain2.get_timeline()) <= 100
