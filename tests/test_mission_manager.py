"""Tests for JARVIS Mission Manager (v5.2.0)."""

import sys
import os
import asyncio
import json
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.mission.manager import MissionManager
from jarvis.mission.mission import Mission, MissionStatus, MissionStage


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Mission Manager Tests
# ════════════════════════════════════════════════════════════

class TestMissionManager:
    def setup_method(self):
        self.manager = MissionManager()

    def test_create_mission(self):
        mission = _run(self.manager.create("Build a web app"))
        assert mission is not None
        assert mission.user_request == "Build a web app"
        assert mission.status == MissionStatus.CREATED
        assert mission.id.startswith("mission_")

    def test_get_mission(self):
        mission = _run(self.manager.create("Test mission"))
        found = _run(self.manager.get(mission.id))
        assert found is not None
        assert found.id == mission.id
        assert found.user_request == "Test mission"

    def test_get_mission_not_found(self):
        found = _run(self.manager.get("nonexistent"))
        assert found is None

    def test_list_active(self):
        _run(self.manager.create("Mission 1"))
        _run(self.manager.create("Mission 2"))
        active = _run(self.manager.list_active())
        assert len(active) == 2
        assert all(m.status in (
            MissionStatus.CREATED, MissionStatus.RESEARCHING,
            MissionStatus.PLANNING, MissionStatus.EXECUTING,
            MissionStatus.VERIFYING, MissionStatus.REVIEWING,
            MissionStatus.PAUSED,
        ) for m in active)

    def test_list_completed(self):
        m = _run(self.manager.create("Completed mission"))
        _run(self.manager.cancel(m.id))
        completed = _run(self.manager.list_completed())
        assert len(completed) == 1
        assert completed[0].status == MissionStatus.FAILED

    def test_start_mission(self):
        mission = _run(self.manager.create("Start me"))
        _run(self.manager.start(mission.id))
        assert mission.status == MissionStatus.RESEARCHING

    def test_start_mission_wrong_status(self):
        mission = _run(self.manager.create("Cannot start"))
        _run(self.manager.start(mission.id))
        _run(self.manager.cancel(mission.id))
        with pytest.raises(RuntimeError):
            _run(self.manager.start(mission.id))

    def test_pause_mission(self):
        mission = _run(self.manager.create("Pause me"))
        _run(self.manager.start(mission.id))
        _run(self.manager.pause(mission.id))
        assert mission.status == MissionStatus.PAUSED

    def test_pause_already_paused(self):
        mission = _run(self.manager.create("Already paused"))
        _run(self.manager.start(mission.id))
        _run(self.manager.pause(mission.id))
        _run(self.manager.pause(mission.id))
        assert mission.status == MissionStatus.PAUSED

    def test_resume_mission(self):
        mission = _run(self.manager.create("Resume me"))
        _run(self.manager.start(mission.id))
        _run(self.manager.pause(mission.id))
        _run(self.manager.resume(mission.id))
        assert mission.status == MissionStatus.EXECUTING

    def test_resume_not_paused(self):
        mission = _run(self.manager.create("Not paused"))
        with pytest.raises(RuntimeError):
            _run(self.manager.resume(mission.id))

    def test_cancel_mission(self):
        mission = _run(self.manager.create("Cancel me"))
        _run(self.manager.cancel(mission.id))
        assert mission.status == MissionStatus.FAILED

    def test_cancel_already_completed(self):
        mission = _run(self.manager.create("Done"))
        _run(self.manager.cancel(mission.id))
        _run(self.manager.cancel(mission.id))
        assert mission.status == MissionStatus.FAILED

    def test_retry_mission(self):
        mission = _run(self.manager.create("Retry me"))
        _run(self.manager.cancel(mission.id))
        _run(self.manager.retry(mission.id))
        assert mission.status == MissionStatus.CREATED
        assert len(mission.errors) == 0

    def test_retry_not_failed(self):
        mission = _run(self.manager.create("Not failed"))
        with pytest.raises(RuntimeError):
            _run(self.manager.retry(mission.id))

    def test_get_progress(self):
        mission = _run(self.manager.create("Progress"))
        progress = _run(self.manager.get_progress(mission.id))
        assert progress["mission_id"] == mission.id
        assert progress["status"] == MissionStatus.CREATED
        assert progress["progress_pct"] == 0.0

    def test_get_eta(self):
        mission = _run(self.manager.create("ETA"))
        _run(self.manager.start(mission.id))
        eta = _run(self.manager.get_eta(mission.id))
        # No steps done yet, so ETA is None
        assert eta is None

    def test_get_eta_with_steps(self):
        mission = _run(self.manager.create("ETA2"))
        _run(self.manager.start(mission.id))
        self.manager._progress[mission.id] = {"steps_total": 10, "steps_done": 2, "status": "running"}
        # Simulate elapsed time
        import time
        self.manager._start_times[mission.id] = time.time() - 10.0
        eta = _run(self.manager.get_eta(mission.id))
        assert eta is not None
        assert eta >= 0

    def test_replay_mission(self):
        mission = _run(self.manager.create("Original"))
        _run(self.manager.start(mission.id))
        clone = _run(self.manager.replay(mission.id))
        assert clone.id != mission.id
        assert "[REPLAY]" in clone.user_request
        assert clone.goal == mission.goal

    def test_create_with_priority(self):
        mission = _run(self.manager.create("High priority", priority="high"))
        assert mission.priority == "high"


# ════════════════════════════════════════════════════════════
# Persistence Tests
# ════════════════════════════════════════════════════════════

class TestMissionManagerPersistence:
    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            storage_path = f.name
        try:
            manager1 = MissionManager(storage_path=storage_path)
            _run(manager1.create("Mission A"))
            _run(manager1.create("Mission B"))
            _run(manager1.save())

            # Verify file exists
            assert os.path.isfile(storage_path)
            with open(storage_path, "r") as f:
                data = json.load(f)
            assert len(data) == 2

            # Load into a new manager
            manager2 = MissionManager(storage_path=storage_path)
            _run(manager2.load())
            active = _run(manager2.list_active())
            assert len(active) == 2
        finally:
            os.unlink(storage_path)

    def test_load_nonexistent_file(self):
        manager = MissionManager(storage_path="/tmp/nonexistent_jarvis_test.json")
        _run(manager.load())
        assert len(manager._missions) == 0

    def test_save_empty(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            storage_path = f.name
        try:
            manager = MissionManager(storage_path=storage_path)
            _run(manager.save())
            assert os.path.isfile(storage_path)
        finally:
            os.unlink(storage_path)


# ════════════════════════════════════════════════════════════
# Error Handling Tests
# ════════════════════════════════════════════════════════════

class TestMissionManagerErrors:
    def test_require_nonexistent(self):
        with pytest.raises(KeyError):
            manager = MissionManager()
            _run(manager.start("nonexistent"))

    def test_get_progress_nonexistent(self):
        with pytest.raises(KeyError):
            manager = MissionManager()
            _run(manager.get_progress("nonexistent"))
