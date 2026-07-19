import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from jarvis.living_dashboard.models import DashboardStatus, ThoughtEntry, WorkerStatus
from jarvis.living_dashboard import LivingDashboard
from jarvis.living_dashboard.manager import LivingDashboardManager


# ---------------------------------------------------------------------------
# DashboardModels
# ---------------------------------------------------------------------------


class TestDashboardModels:
    def test_worker_status_creation(self):
        w = WorkerStatus(
            name="BrainWorker",
            role="analyst",
            current_task="analyzing context",
            confidence=0.85,
            status="active",
            last_active="2025-06-15T10:30:00Z",
        )
        assert w.name == "BrainWorker"
        assert w.confidence == 0.85
        assert w.status == "active"

    def test_worker_status_to_dict(self):
        w = WorkerStatus(
            name="W1", role="dev", current_task="coding",
            confidence=0.9, status="idle", last_active="2025-01-01T00:00:00Z",
        )
        d = w.to_dict()
        assert d["name"] == "W1"
        assert d["status"] == "idle"
        assert d["confidence"] == 0.9

    def test_thought_entry_creation(self):
        t = ThoughtEntry(
            timestamp="2025-06-15T10:30:00Z",
            content="User likely needs to commit",
            category="prediction",
            confidence=0.7,
            actions_proposed=["suggest commit"],
        )
        assert t.content == "User likely needs to commit"
        assert t.actions_proposed == ["suggest commit"]

    def test_thought_entry_to_dict(self):
        t = ThoughtEntry(
            timestamp="2025-01-01T00:00:00Z",
            content="Testing",
            category="test",
            confidence=0.5,
        )
        d = t.to_dict()
        assert d["category"] == "test"
        assert d["actions_proposed"] == []

    def test_dashboard_status_defaults(self):
        ds = DashboardStatus(
            timestamp="2025-06-15T10:00:00Z",
            neural_core_status="standby",
        )
        assert ds.neural_core_status == "standby"
        assert ds.mission_queue == []
        assert ds.thoughts == []
        assert ds.workers == []
        assert ds.system_metrics == {}
        assert ds.uptime == 0.0

    def test_dashboard_status_to_dict(self):
        ds = DashboardStatus(
            timestamp="2025-06-15T10:00:00Z",
            neural_core_status="online",
            current_project="jarvis",
            uptime=123.45,
        )
        d = ds.to_dict()
        assert d["neural_core_status"] == "online"
        assert d["current_project"] == "jarvis"
        assert d["uptime"] == 123.45
        assert d["timestamp"] == "2025-06-15T10:00:00Z"

    def test_dashboard_status_nested_data(self):
        ds = DashboardStatus(
            timestamp="2025-06-15T10:00:00Z",
            neural_core_status="online",
            thoughts=[{"content": "test", "confidence": 0.5}],
            workers=[{"name": "W1", "status": "active"}],
            suggestions=[{"title": "S1", "priority": "high"}],
        )
        d = ds.to_dict()
        assert len(d["thoughts"]) == 1
        assert d["workers"][0]["name"] == "W1"
        assert d["suggestions"][0]["priority"] == "high"


# ---------------------------------------------------------------------------
# LivingDashboard
# ---------------------------------------------------------------------------


class TestLivingDashboard:
    @pytest.fixture
    def dashboard(self):
        return LivingDashboard()

    def test_init(self, dashboard):
        assert dashboard._mgr is not None

    def test_get_status(self, dashboard):
        result = asyncio.get_event_loop().run_until_complete(dashboard.get_status())
        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "neural_core_status" in result
        assert "mission_queue" in result
        assert "thoughts" in result
        assert "workers" in result
        assert "recent_memories" in result
        assert "timeline" in result
        assert "suggestions" in result
        assert "system_metrics" in result
        assert "uptime" in result

    def test_get_mission_queue(self, dashboard):
        result = asyncio.get_event_loop().run_until_complete(dashboard.get_mission_queue())
        assert isinstance(result, list)

    def test_get_thoughts(self, dashboard):
        result = asyncio.get_event_loop().run_until_complete(dashboard.get_thoughts())
        assert isinstance(result, list)

    def test_get_workers_status(self, dashboard):
        result = asyncio.get_event_loop().run_until_complete(dashboard.get_workers_status())
        assert isinstance(result, list)

    def test_get_recent_memories(self, dashboard):
        result = asyncio.get_event_loop().run_until_complete(dashboard.get_recent_memories(limit=5))
        assert isinstance(result, list)

    def test_get_timeline(self, dashboard):
        result = asyncio.get_event_loop().run_until_complete(dashboard.get_timeline(hours=24))
        assert isinstance(result, list)

    def test_get_suggestions(self, dashboard):
        result = asyncio.get_event_loop().run_until_complete(dashboard.get_suggestions())
        assert isinstance(result, list)

    def test_get_system_metrics(self, dashboard):
        result = asyncio.get_event_loop().run_until_complete(dashboard.get_system_metrics())
        assert isinstance(result, dict)
        assert "uptime_seconds" in result
        assert "cpu_count" in result

    def test_to_websocket_payload(self, dashboard):
        payload = asyncio.get_event_loop().run_until_complete(dashboard.to_websocket_payload())
        assert isinstance(payload, dict)
        required_keys = [
            "timestamp", "neural_core_status", "mission_queue", "thoughts",
            "workers", "recent_memories", "timeline", "suggestions",
            "current_project", "system_metrics", "uptime",
        ]
        for key in required_keys:
            assert key in payload, f"Missing key: {key}"

    def test_websocket_payload_status_standalone(self):
        mgr = LivingDashboardManager()
        payload = asyncio.get_event_loop().run_until_complete(mgr.to_websocket_payload())
        assert payload["neural_core_status"] in ("online", "standby")
        assert isinstance(payload["system_metrics"], dict)
