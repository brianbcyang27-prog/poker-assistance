import sys
import os
import asyncio
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime
from jarvis.projects.models import BuildStatus, Project, ProjectActivity
from jarvis.projects import ProjectManager


# ---------------------------------------------------------------------------
# ProjectModels
# ---------------------------------------------------------------------------


class TestProjectModels:
    def test_project_creation(self):
        p = Project(
            id="abc123",
            name="jarvis",
            purpose="AI assistant",
            path="/Users/brianyang/jarvis",
        )
        assert p.id == "abc123"
        assert p.name == "jarvis"
        assert p.purpose == "AI assistant"
        assert p.path == "/Users/brianyang/jarvis"
        assert p.languages == []
        assert p.frameworks == []
        assert p.build_status == BuildStatus.UNKNOWN

    def test_project_to_dict(self):
        p = Project(
            id="p1", name="test", purpose="testing", path="/tmp/test",
            languages=["Python"], frameworks=["FastAPI"],
            build_status=BuildStatus.PASSING,
        )
        d = p.to_dict()
        assert d["id"] == "p1"
        assert d["languages"] == ["Python"]
        assert d["build_status"] == "passing"
        assert d["last_accessed"] is None

    def test_project_from_dict_roundtrip(self):
        p = Project(
            id="rt-2", name="roundtrip", purpose="test", path="/tmp/rt",
            languages=["Python", "JavaScript"],
            last_accessed=datetime(2025, 6, 15, 10, 0),
        )
        d = p.to_dict()
        p2 = Project.from_dict(d)
        assert p2.id == p.id
        assert p2.languages == ["Python", "JavaScript"]
        assert p2.last_accessed.year == 2025

    def test_project_from_dict_no_last_accessed(self):
        d = {
            "id": "x", "name": "x", "purpose": "x", "path": "/tmp",
            "last_accessed": None,
        }
        p = Project.from_dict(d)
        assert p.last_accessed is None

    def test_project_activity_creation(self):
        a = ProjectActivity(
            timestamp=datetime(2025, 1, 1),
            action="created",
            detail="Created new module",
            files_affected=["module.py"],
        )
        assert a.action == "created"
        assert a.files_affected == ["module.py"]

    def test_project_activity_to_dict(self):
        a = ProjectActivity(
            timestamp=datetime(2025, 3, 20, 14, 30),
            action="modified",
            detail="Updated README",
        )
        d = a.to_dict()
        assert d["action"] == "modified"
        assert d["timestamp"] == "2025-03-20T14:30:00"

    def test_project_activity_from_dict(self):
        d = {
            "timestamp": "2025-04-10T09:00:00",
            "action": "committed",
            "detail": "fix: resolve crash",
            "files_affected": ["crash.py"],
        }
        a = ProjectActivity.from_dict(d)
        assert a.action == "committed"
        assert a.files_affected == ["crash.py"]

    def test_build_status_values(self):
        assert BuildStatus.UNKNOWN.value == "unknown"
        assert BuildStatus.PASSING.value == "passing"
        assert BuildStatus.FAILING.value == "failing"
        assert BuildStatus.BUILDING.value == "building"

    def test_project_context_snapshot(self):
        p = Project(
            id="ctx", name="ctx", purpose="test", path="/tmp",
            context_snapshot={"last_file": "main.py", "cursor_line": 42},
        )
        assert p.context_snapshot["last_file"] == "main.py"
        assert p.context_snapshot["cursor_line"] == 42


# ---------------------------------------------------------------------------
# ProjectManager
# ---------------------------------------------------------------------------


class TestProjectManager:
    @pytest.fixture
    def manager(self, tmp_path):
        storage = str(tmp_path / "projects.json")
        return ProjectManager(storage_path=storage)

    def test_init(self, manager):
        assert manager._projects == {}
        assert manager._active_project_id is None

    def test_scan_jarvis_repo(self, manager):
        projects = asyncio.get_event_loop().run_until_complete(
            manager.scan_projects(os.path.expanduser("~"))
        )
        assert isinstance(projects, list)
        jarvis_projects = [p for p in projects if p.name == "jarvis"]
        assert len(jarvis_projects) >= 1
        assert "Python" in jarvis_projects[0].languages

    def test_scan_nonexistent_dir(self, manager):
        projects = asyncio.get_event_loop().run_until_complete(
            manager.scan_projects("/nonexistent/path/xyz")
        )
        assert projects == []

    def test_get_project(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.scan_projects(os.path.expanduser("~"))
        )
        jarvis_id = None
        for pid, p in manager._projects.items():
            if p.name == "jarvis":
                jarvis_id = pid
                break
        assert jarvis_id is not None
        project = asyncio.get_event_loop().run_until_complete(manager.get_project(jarvis_id))
        assert project is not None
        assert project.name == "jarvis"

    def test_set_active_project(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.scan_projects(os.path.expanduser("~"))
        )
        jarvis_id = list(manager._projects.keys())[0]
        asyncio.get_event_loop().run_until_complete(manager.set_active_project(jarvis_id))
        active = asyncio.get_event_loop().run_until_complete(manager.get_active_project())
        assert active is not None
        assert active.id == jarvis_id

    def test_get_active_project_none(self, manager):
        active = asyncio.get_event_loop().run_until_complete(manager.get_active_project())
        assert active is None

    def test_get_history(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.scan_projects(os.path.expanduser("~"))
        )
        pid = list(manager._projects.keys())[0]
        asyncio.get_event_loop().run_until_complete(
            manager.log_activity(pid, "modified", "Updated config")
        )
        history = asyncio.get_event_loop().run_until_complete(manager.get_project_history(pid))
        assert len(history) == 1
        assert history[0]["action"] == "modified"

    def test_restore_context_empty(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.scan_projects(os.path.expanduser("~"))
        )
        pid = list(manager._projects.keys())[0]
        ctx = asyncio.get_event_loop().run_until_complete(manager.restore_context(pid))
        assert isinstance(ctx, dict)

    def test_save_and_load(self, tmp_path):
        storage = str(tmp_path / "projects.json")
        m1 = ProjectManager(storage_path=storage)
        asyncio.get_event_loop().run_until_complete(
            m1.scan_projects(os.path.expanduser("~"))
        )
        asyncio.get_event_loop().run_until_complete(m1.save())

        m2 = ProjectManager(storage_path=storage)
        asyncio.get_event_loop().run_until_complete(m2.load())
        assert len(m2._projects) >= 1

    def test_project_languages_detected(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.scan_projects(os.path.expanduser("~"))
        )
        jarvis = None
        for p in manager._projects.values():
            if p.name == "jarvis":
                jarvis = p
                break
        if jarvis is not None:
            assert "Python" in jarvis.languages

    def test_project_has_git_info(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.scan_projects(os.path.expanduser("~"))
        )
        jarvis = None
        for p in manager._projects.values():
            if p.name == "jarvis":
                jarvis = p
                break
        if jarvis is not None:
            assert jarvis.git_branch is not None or jarvis.git_remote is not None

    def test_log_activity_trimming(self, manager):
        asyncio.get_event_loop().run_until_complete(
            manager.scan_projects(os.path.expanduser("~"))
        )
        pid = list(manager._projects.keys())[0]
        for i in range(210):
            asyncio.get_event_loop().run_until_complete(
                manager.log_activity(pid, "tick", f"event_{i}")
            )
        assert len(manager._activities[pid]) <= 200
