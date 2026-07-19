import sys
import os
import asyncio
import json
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from jarvis.context.models import ContextSummary, CurrentContext, TimelineEvent
from jarvis.context import ContextEngine


# ---------------------------------------------------------------------------
# ContextModels
# ---------------------------------------------------------------------------


class TestContextModels:
    def test_current_context_defaults(self):
        ctx = CurrentContext()
        assert isinstance(ctx.timestamp, float)
        assert ctx.active_app == ""
        assert ctx.active_file == ""
        assert ctx.git_branch == ""
        assert ctx.git_repo == ""
        assert ctx.browser_tabs == []
        assert ctx.open_files == []
        assert ctx.running_terminals == []
        assert ctx.current_mission == ""
        assert ctx.connected_devices == []
        assert ctx.recent_conversations == []
        assert ctx.current_project == ""
        assert ctx.current_language == ""
        assert ctx.cpu_percent == 0.0
        assert ctx.memory_percent == 0.0
        assert ctx.uptime_seconds == 0.0
        assert ctx.context_dict == {}

    def test_current_context_custom(self):
        ctx = CurrentContext(
            active_app="Terminal",
            active_file="/tmp/main.py",
            git_branch="develop",
            git_repo="jarvis",
            browser_tabs=["https://google.com"],
            cpu_percent=33.3,
            memory_percent=55.5,
        )
        assert ctx.active_app == "Terminal"
        assert ctx.git_branch == "develop"
        assert ctx.cpu_percent == 33.3

    def test_timeline_event_defaults(self):
        e = TimelineEvent()
        assert isinstance(e.id, str)
        assert len(e.id) == 12
        assert isinstance(e.timestamp, float)
        assert e.category == "system"
        assert e.action == "observed"
        assert e.detail == ""
        assert e.metadata == {}

    def test_timeline_event_custom(self):
        e = TimelineEvent(
            category="file",
            action="modified",
            detail="main.py",
            metadata={"size": 100},
        )
        assert e.category == "file"
        assert e.action == "modified"
        assert e.metadata["size"] == 100

    def test_timeline_event_unique_ids(self):
        e1 = TimelineEvent()
        e2 = TimelineEvent()
        assert e1.id != e2.id

    def test_context_summary_defaults(self):
        s = ContextSummary()
        assert isinstance(s.timestamp, float)
        assert s.active_project == ""
        assert s.today_events_count == 0
        assert s.active_apps == []
        assert s.recent_files == []
        assert s.recent_commits == []
        assert s.current_focus == ""
        assert s.outstanding_tasks == []


# ---------------------------------------------------------------------------
# ContextEngine
# ---------------------------------------------------------------------------


class TestContextEngine:
    @pytest.fixture
    def tmp_data_dir(self, tmp_path):
        return tmp_path / "context_data"

    @pytest.fixture
    def engine(self, tmp_data_dir):
        return ContextEngine(data_dir=tmp_data_dir)

    def test_init_defaults(self):
        e = ContextEngine()
        stats = e.get_stats()
        assert stats["running"] is False
        assert stats["timeline_size"] == 0
        assert stats["timeline_max"] == 1000
        assert "system" in stats["categories"]

    def test_init_custom_dir(self, tmp_data_dir):
        e = ContextEngine(data_dir=tmp_data_dir)
        stats = e.get_stats()
        assert str(tmp_data_dir) in stats["data_dir"]

    def test_update_context(self, engine):
        asyncio.get_event_loop().run_until_complete(
            engine.update("app", {"active": "VSCode"})
        )
        ctx = asyncio.get_event_loop().run_until_complete(engine.get_current_context())
        assert ctx.active_app == "VSCode"

    def test_update_multiple_categories(self, engine):
        asyncio.get_event_loop().run_until_complete(engine.update("app", {"active": "Terminal"}))
        asyncio.get_event_loop().run_until_complete(engine.update("file", {"active": "main.py"}))
        asyncio.get_event_loop().run_until_complete(engine.update("git", {"branch": "main", "repo": "jarvis"}))
        ctx = asyncio.get_event_loop().run_until_complete(engine.get_current_context())
        assert ctx.active_app == "Terminal"
        assert ctx.active_file == "main.py"
        assert ctx.git_branch == "main"
        assert ctx.git_repo == "jarvis"

    def test_add_timeline_event(self, engine):
        event = TimelineEvent(category="code", action="created", detail="new_module.py")
        asyncio.get_event_loop().run_until_complete(engine.add_timeline_event(event))
        timeline = asyncio.get_event_loop().run_until_complete(engine.get_timeline(hours=1))
        assert len(timeline) == 1
        assert timeline[0].detail == "new_module.py"

    def test_search_timeline(self, engine):
        e1 = TimelineEvent(category="file", action="modified", detail="main.py was changed")
        e2 = TimelineEvent(category="git", action="committed", detail="fix: resolved bug in login")
        e3 = TimelineEvent(category="file", action="created", detail="test_main.py was added")
        asyncio.get_event_loop().run_until_complete(engine.add_timeline_event(e1))
        asyncio.get_event_loop().run_until_complete(engine.add_timeline_event(e2))
        asyncio.get_event_loop().run_until_complete(engine.add_timeline_event(e3))
        results = asyncio.get_event_loop().run_until_complete(engine.search_timeline("main"))
        assert len(results) >= 1

    def test_search_timeline_no_match(self, engine):
        event = TimelineEvent(category="system", action="observed", detail="nothing interesting")
        asyncio.get_event_loop().run_until_complete(engine.add_timeline_event(event))
        results = asyncio.get_event_loop().run_until_complete(engine.search_timeline("xyznonexistent"))
        assert len(results) == 0

    def test_get_summary(self, engine):
        asyncio.get_event_loop().run_until_complete(engine.update("app", {"active": "VSCode"}))
        summary = asyncio.get_event_loop().run_until_complete(engine.get_summary())
        assert isinstance(summary, ContextSummary)
        assert summary.active_apps == ["VSCode"]

    def test_get_stats(self, engine):
        stats = engine.get_stats()
        assert "running" in stats
        assert "timeline_size" in stats
        assert "categories" in stats
        assert "uptime_seconds" in stats

    def test_save_and_load(self, tmp_data_dir):
        tmp_data_dir.mkdir(parents=True, exist_ok=True)
        e1 = ContextEngine(data_dir=tmp_data_dir)
        asyncio.get_event_loop().run_until_complete(e1.update("app", {"active": "Editor"}))
        event = TimelineEvent(category="file", action="saved", detail="test.py")
        asyncio.get_event_loop().run_until_complete(e1.add_timeline_event(event))
        asyncio.get_event_loop().run_until_complete(e1.save())

        e2 = ContextEngine(data_dir=tmp_data_dir)
        asyncio.get_event_loop().run_until_complete(e2.load())
        ctx = asyncio.get_event_loop().run_until_complete(e2.get_current_context())
        assert ctx.active_app == "Editor"

    def test_save_load_timeline(self, tmp_data_dir):
        tmp_data_dir.mkdir(parents=True, exist_ok=True)
        e1 = ContextEngine(data_dir=tmp_data_dir)
        for i in range(3):
            ev = TimelineEvent(category="system", action="tick", detail=f"event_{i}")
            asyncio.get_event_loop().run_until_complete(e1.add_timeline_event(ev))
        asyncio.get_event_loop().run_until_complete(e1.save())

        e2 = ContextEngine(data_dir=tmp_data_dir)
        asyncio.get_event_loop().run_until_complete(e2.load())
        timeline = asyncio.get_event_loop().run_until_complete(e2.get_timeline(hours=24))
        assert len(timeline) == 3

    def test_timeline_event_metadata(self, engine):
        event = TimelineEvent(
            category="app",
            action="switched",
            detail="Switched to Chrome",
            metadata={"from": "Terminal", "duration_s": 5},
        )
        asyncio.get_event_loop().run_until_complete(engine.add_timeline_event(event))
        timeline = asyncio.get_event_loop().run_until_complete(engine.get_timeline(hours=1))
        assert timeline[0].metadata["from"] == "Terminal"
