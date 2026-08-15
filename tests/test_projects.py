"""Tests for the Project Intelligence backend (v9.0.0 M2) — ProjectManager,
complexity estimation, and the task-flow router."""

import asyncio
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.core.database import Database
from jarvis.projects import manager as manager_module
from jarvis.projects.complexity import estimate_complexity, suggest_action
from jarvis.projects.manager import project_manager
from jarvis.projects.task_flow import route_task, select_domain

_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)


def _run(coro):
    return _loop.run_until_complete(coro)


def _unique(prefix: str) -> str:
    return f"{prefix}-{str(uuid.uuid4())[:8]}"


@pytest.fixture()
def test_db(tmp_path):
    """Fresh Database on a temp file, patched into the project manager modules."""
    import copy

    db = Database()
    db._config = copy.copy(db._config)
    db._config.db_path = tmp_path / "test.db"
    _run(db.connect())
    _run(
        db.executescript(
            "DELETE FROM project_missions; "
            "DELETE FROM project_artifacts; "
            "DELETE FROM project_decisions; "
            "DELETE FROM project_knowledge; "
            "DELETE FROM projects;"
        )
    )
    _run(db._db.commit())

    original = manager_module.get_db

    async def fake_get_db():
        return db

    manager_module.get_db = fake_get_db
    yield db
    manager_module.get_db = original
    _run(db.close())


# ════════════════════════════════════════════════════════════
# Complexity estimation
# ════════════════════════════════════════════════════════════


class TestComplexity:
    def test_tiny_request(self):
        result = estimate_complexity("hello")
        assert result["level"] == "tiny"
        assert result["suggested_action"] == "direct"

    def test_short_greeting_not_mission(self):
        result = estimate_complexity("what time is it?")
        assert result["level"] in ("tiny", "small")
        assert result["score"] < 55

    def test_build_request_is_mission_or_higher(self):
        result = estimate_complexity(
            "Build a new API endpoint for the dashboard and add tests for it"
        )
        assert result["score"] >= 25
        assert result["level"] in ("small", "mission", "project")

    def test_long_multi_goal_is_project(self):
        result = estimate_complexity(
            "Build a complete expense tracker web app with a backend API, "
            "database schema, frontend dashboard, and deployment setup, then "
            "write documentation and tests for everything. Also add a report "
            "generator and design document. This is a big multi-part project "
            "that will take several days and touch many files."
        )
        assert result["level"] == "project"
        assert result["suggested_action"] == "create_project"

    def test_suggest_action_mapping(self):
        assert suggest_action("tiny") == "direct"
        assert suggest_action("small") == "mission"
        assert suggest_action("mission") == "mission"
        assert suggest_action("project") == "create_project"


# ════════════════════════════════════════════════════════════
# Domain selection
# ════════════════════════════════════════════════════════════


class TestDomainSelection:
    def test_education_alias(self):
        assert select_domain("Please tutor me on linear algebra") == "education"

    def test_finance_alias(self):
        assert select_domain("help me make a budget for next month") == "finance"

    def test_default_engineering(self):
        assert select_domain("no domain keywords here") == "engineering"


# ════════════════════════════════════════════════════════════
# ProjectManager CRUD
# ════════════════════════════════════════════════════════════


class TestProjectManager:
    def test_create_and_get_project(self, test_db):
        name = _unique("pm-create")
        project = _run(project_manager.create_project(name, "test project", "education"))
        assert project.name == name
        assert project.domain == "education"
        assert project.status == "active"

        fetched = _run(project_manager.get_project(project.id))
        assert fetched is not None
        assert fetched.id == project.id

    def test_create_duplicate_name_returns_existing(self, test_db):
        name = _unique("pm-dup")
        first = _run(project_manager.create_project(name))
        second = _run(project_manager.create_project(name))
        assert first.id == second.id

    def test_update_project(self, test_db):
        name = _unique("pm-update")
        project = _run(project_manager.create_project(name))
        updated = _run(project_manager.update_project(project.id, status="paused"))
        assert updated.status == "paused"

    def test_list_projects(self, test_db):
        name = _unique("pm-list")
        _run(project_manager.create_project(name))
        projects = _run(project_manager.list_projects())
        assert any(p.name == name for p in projects)

    def test_resolve_project_for_request(self, test_db):
        name = _unique("resolve-me")
        project = _run(project_manager.create_project(name))
        resolved = _run(project_manager.resolve_project_for_request(f"work on {name} today"))
        assert resolved == project.id

    def test_mission_lifecycle(self, test_db):
        name = _unique("pm-mission")
        project = _run(project_manager.create_project(name))
        mission = _run(
            project_manager.add_mission(project.id, "Build feature X", "goal text", "small")
        )
        assert mission.status == "planned"
        assert mission.complexity == "small"

        _run(project_manager.update_mission(mission.id, status="active"))
        missions = _run(project_manager.list_missions(project_id=project.id))
        assert len(missions) == 1
        assert missions[0].status == "active"

    def test_artifact_and_decision(self, test_db):
        name = _unique("pm-artifact")
        project = _run(project_manager.create_project(name))
        artifact = _run(
            project_manager.add_artifact(project.id, "design doc", "report", "content here")
        )
        assert artifact.artifact_type == "report"

        decision = _run(
            project_manager.add_decision(project.id, "framework", "use FastAPI", "team choice")
        )
        assert decision.decision == "use FastAPI"

        artifacts = _run(project_manager.list_artifacts(project.id))
        decisions = _run(project_manager.list_decisions(project.id))
        assert len(artifacts) == 1
        assert len(decisions) == 1

    def test_knowledge_graph(self, test_db):
        name = _unique("pm-knowledge")
        project = _run(project_manager.create_project(name))
        node_a = _run(project_manager.add_knowledge(project.id, "API design", "concept"))
        node_b = _run(
            project_manager.add_knowledge(project.id, "FastAPI", "domain", links=[node_a.id])
        )
        nodes = _run(project_manager.list_knowledge(project.id))
        assert len(nodes) == 2
        by_id = {n.id: n for n in nodes}
        assert by_id[node_b.id].links == [node_a.id]

    def test_dashboard_aggregates(self, test_db):
        name = _unique("pm-dashboard")
        project = _run(project_manager.create_project(name))
        _run(project_manager.add_mission(project.id, "M1", "g1", "small"))
        _run(project_manager.add_mission(project.id, "M2", "g2", "small"))
        missions = _run(project_manager.list_missions(project_id=project.id))
        _run(project_manager.update_mission(missions[0].id, status="completed"))

        data = _run(project_manager.dashboard(project.id))
        assert data["mission_statuses"]["completed"] == 1
        assert data["mission_statuses"]["planned"] == 1
        assert data["progress"] == 50.0

    def test_timeline_shape(self, test_db):
        name = _unique("pm-timeline")
        project = _run(project_manager.create_project(name))
        _run(project_manager.add_mission(project.id, "A", "g", "small"))
        _run(project_manager.add_mission(project.id, "B", "g", "small"))
        timeline = _run(project_manager.timeline(project.id))
        assert len(timeline["nodes"]) == 2
        assert len(timeline["edges"]) == 1


# ════════════════════════════════════════════════════════════
# Task-flow routing
# ════════════════════════════════════════════════════════════


class TestTaskFlow:
    def test_tiny_request_skips(self, test_db):
        result = _run(route_task("hello there", domain_registry=None))
        assert result["skipped"] is True

    def test_project_request_creates_project_and_mission(self, test_db):
        events = []

        async def emit(event):
            events.append(event)

        _run(
            route_task(
                "Build a new web dashboard with a backend API, database schema, "
                "and deployment configuration, then write tests and docs",
                domain_registry=None,
                emit=emit,
            )
        )
        types = [e["type"] for e in events]
        assert "project_resolved" in types
        assert "domain_selected" in types
        assert "mission_start" in types
        assert "mission_step" in types

    def test_mission_level_uses_existing_project_match(self, test_db):
        name = _unique("flow-resolve")
        project = _run(project_manager.create_project(name))
        result = _run(
            route_task(
                f"Add a feature to {name} and test it thoroughly",
                domain_registry=None,
            )
        )
        assert result["project_id"] == project.id

    def test_domain_selection_via_registry(self, test_db):
        events = []

        async def emit(event):
            events.append(event)

        _run(
            route_task(
                "Tutor me through a Python course: create curriculum and "
                "assessment materials for the class",
                domain_registry=None,
                emit=emit,
            )
        )
        domain_events = [e for e in events if e["type"] == "domain_selected"]
        assert domain_events
        assert domain_events[0]["payload"]["domain"] == "education"


class _FakeMaster:
    def __init__(self):
        self.calls = 0

    async def execute_task(self, task):
        from jarvis.core.models import AgentMessage

        self.calls += 1
        return AgentMessage(
            sender="engineering",
            receiver="J",
            task_id=task.id,
            content="Built the dashboard with a FastAPI backend.",
            status="completed",
            confidence=0.92,
            issues=[],
        )


class _FakeRegistry:
    def __init__(self, master):
        self._master = master

    def get(self, domain):
        return self._master


_MISSION_TEXT = (
    "Build a new web dashboard with a backend API, database schema, "
    "and deployment configuration, then write tests and docs"
)


class TestDashboardLiving:
    def test_dashboard_aggregates_living_fields(self, test_db):
        async def emit(event):
            pass

        result = _run(
            route_task(
                _MISSION_TEXT,
                domain_registry=_FakeRegistry(_FakeMaster()),
                emit=emit,
                fact_checker=lambda title, content: (
                    {"verified": True, "issues": [], "summary": "ok"}
                ),
            )
        )
        project_id = result["project_id"]
        data = _run(project_manager.dashboard(project_id))

        assert data["current_mission"] is not None
        assert data["current_mission"]["id"] == result["mission"]["id"]
        assert data["confidence"] == 0.92
        kinds = [a["kind"] for a in data["recent_activity"]]
        assert "mission" in kinds
        assert "artifact" in kinds
        assert "decision" in kinds
        assert data["progress"] == 100.0

    def test_dashboard_confidence_none_without_report(self, test_db):
        project = _run(
            project_manager.create_project(name="live-empty", description="", domain="engineering")
        )
        data = _run(project_manager.dashboard(project.id))
        assert data["current_mission"] is None
        assert data["confidence"] is None
        assert data["recent_activity"] == []


class TestFactCheckGate:
    def test_fact_check_gate_and_report(self, test_db):
        events = []
        fc_calls = []

        async def emit(event):
            events.append(event)

        async def fake_fact_checker(title, content):
            fc_calls.append((title, content))
            return {"verified": True, "issues": [], "summary": "all claims verified"}

        master = _FakeMaster()
        result = _run(
            route_task(
                _MISSION_TEXT,
                domain_registry=_FakeRegistry(master),
                emit=emit,
                fact_checker=fake_fact_checker,
            )
        )

        assert result["skipped"] is False
        assert master.calls == 1
        assert len(fc_calls) == 1
        types = [e["type"] for e in events]
        assert "mission_factcheck" in types
        assert "mission_report" in types
        report_event = next(e for e in events if e["type"] == "mission_report")
        report = report_event["payload"]["report"]
        assert "# Mission Report" in report
        assert "Fact check**: verified" in report
        assert "## Result" in report
        artifacts = _run(project_manager.list_artifacts(result["project_id"]))
        assert any(a.name == "mission report" for a in artifacts)

    def test_mission_events_published_to_bus(self, test_db):
        from jarvis.core.events import event_bus

        received = []

        async def capture(event):
            received.append(event.type)

        async def emit(event):
            pass

        async def scenario():
            await event_bus.on("mission.*", capture)
            try:
                await route_task(
                    _MISSION_TEXT,
                    domain_registry=_FakeRegistry(_FakeMaster()),
                    emit=emit,
                )
            finally:
                await event_bus.off("mission.*", capture)

        _run(scenario())
        assert "mission.start" in received
        assert "mission.report" in received

    def test_fact_check_gate_skipped_without_checker(self, test_db):
        master = _FakeMaster()
        result = _run(
            route_task(_MISSION_TEXT, domain_registry=_FakeRegistry(master))
        )
        assert result["skipped"] is False
        assert master.calls == 1
        artifacts = _run(project_manager.list_artifacts(result["project_id"]))
        assert any(a.name == "mission report" for a in artifacts)
