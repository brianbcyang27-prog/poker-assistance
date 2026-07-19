import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timedelta
from jarvis.suggestions.models import Suggestion, SuggestionCategory, SuggestionPriority, SuggestionStats
from jarvis.suggestions import SuggestionEngine


# ---------------------------------------------------------------------------
# SuggestionModels
# ---------------------------------------------------------------------------


class TestSuggestionModels:
    def test_suggestion_creation(self):
        s = Suggestion(
            id="abc-123",
            timestamp=datetime(2025, 1, 15, 10, 30),
            title="Commit your work",
            description="No commits in 4 hours",
            confidence=0.75,
            category=SuggestionCategory.COMMIT,
            priority=SuggestionPriority.MEDIUM,
        )
        assert s.id == "abc-123"
        assert s.title == "Commit your work"
        assert s.confidence == 0.75
        assert s.category == SuggestionCategory.COMMIT
        assert s.priority == SuggestionPriority.MEDIUM
        assert s.dismissed is False
        assert s.acknowledged is False
        assert s.auto_dismiss_threshold == 0.3

    def test_suggestion_to_dict(self):
        s = Suggestion(
            id="x",
            timestamp=datetime(2025, 6, 1, 12, 0),
            title="Title",
            description="Desc",
            confidence=0.5,
            category=SuggestionCategory.BUG,
            priority=SuggestionPriority.HIGH,
        )
        d = s.to_dict()
        assert d["id"] == "x"
        assert d["category"] == "bug"
        assert d["priority"] == "high"
        assert d["timestamp"] == "2025-06-01T12:00:00"

    def test_suggestion_from_dict_roundtrip(self):
        s = Suggestion(
            id="rt-1",
            timestamp=datetime(2025, 3, 10, 8, 0),
            title="Test roundtrip",
            description="Should survive serialization",
            confidence=0.6,
            category=SuggestionCategory.TEST,
            priority=SuggestionPriority.LOW,
            dismissed=True,
        )
        d = s.to_dict()
        s2 = Suggestion.from_dict(d)
        assert s2.id == s.id
        assert s2.title == s.title
        assert s2.confidence == s.confidence
        assert s2.category == s.category
        assert s2.dismissed is True

    def test_suggestion_stats_defaults(self):
        stats = SuggestionStats()
        assert stats.total_generated == 0
        assert stats.total_dismissed == 0
        assert stats.acceptance_rate == 0.0
        assert stats.by_category == {}

    def test_suggestion_stats_to_dict(self):
        stats = SuggestionStats(
            total_generated=10,
            total_dismissed=2,
            acceptance_rate=0.8,
            by_category={"commit": 5, "bug": 5},
        )
        d = stats.to_dict()
        assert d["total_generated"] == 10
        assert d["by_category"]["commit"] == 5

    def test_suggestion_category_values(self):
        assert SuggestionCategory.COMMIT.value == "commit"
        assert SuggestionCategory.BUG.value == "bug"
        assert SuggestionCategory.REFACTOR.value == "refactor"
        assert SuggestionCategory.TEST.value == "test"

    def test_suggestion_priority_values(self):
        assert SuggestionPriority.LOW.value == "low"
        assert SuggestionPriority.MEDIUM.value == "medium"
        assert SuggestionPriority.HIGH.value == "high"


# ---------------------------------------------------------------------------
# SuggestionEngine
# ---------------------------------------------------------------------------


class TestSuggestionEngine:
    @pytest.fixture
    def engine(self):
        return SuggestionEngine()

    def test_init(self, engine):
        assert engine._suggestions == []
        assert engine._dismissed_ids == set()
        assert engine._stats.total_generated == 0

    def test_analyze_empty_context(self, engine):
        results = asyncio.get_event_loop().run_until_complete(
            engine.analyze({}, [])
        )
        assert isinstance(results, list)
        assert len(results) == 0

    def test_analyze_no_recent_commits(self, engine):
        context = {"last_commit_time": (datetime.now() - timedelta(hours=5)).isoformat()}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        assert len(results) >= 1
        commit_suggestions = [s for s in results if s.category == SuggestionCategory.COMMIT]
        assert len(commit_suggestions) == 1
        assert commit_suggestions[0].confidence > 0.5

    def test_analyze_recent_commits_no_suggestion(self, engine):
        context = {"last_commit_time": (datetime.now() - timedelta(hours=1)).isoformat()}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        commit_suggestions = [s for s in results if s.category == SuggestionCategory.COMMIT]
        assert len(commit_suggestions) == 0

    def test_analyze_large_files(self, engine):
        context = {"large_files": [{"name": "big.py", "lines": 800}]}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        refactor = [s for s in results if s.category == SuggestionCategory.REFACTOR]
        assert len(refactor) == 1
        assert "800" in refactor[0].description

    def test_analyze_no_tests(self, engine):
        context = {"has_tests": False}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        test_suggs = [s for s in results if s.category == SuggestionCategory.TEST]
        assert len(test_suggs) == 1
        assert test_suggs[0].confidence == 0.75

    def test_analyze_build_failure(self, engine):
        context = {"build_failed": True, "build_error": "SyntaxError on line 42"}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        bugs = [s for s in results if s.category == SuggestionCategory.BUG]
        assert len(bugs) == 1
        assert bugs[0].confidence == 0.95

    def test_analyze_stale_todos(self, engine):
        context = {"todo_count": 8}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        reminders = [s for s in results if s.category == SuggestionCategory.REMINDER]
        assert len(reminders) == 1
        assert reminders[0].priority == SuggestionPriority.MEDIUM

    def test_analyze_circular_imports(self, engine):
        context = {"circular_imports": [("jarvis.a", "jarvis.b")]}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        bugs = [s for s in results if s.category == SuggestionCategory.BUG]
        assert any("Circular" in s.title for s in bugs)

    def test_analyze_missing_docs(self, engine):
        context = {"missing_docstrings": ["module_a.py", "module_b.py"]}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        docs = [s for s in results if s.category == SuggestionCategory.DOCUMENTATION]
        assert len(docs) == 1

    def test_analyze_dead_code(self, engine):
        context = {"dead_code": ["unused_func", "old_helper"]}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        refactor = [s for s in results if s.category == SuggestionCategory.REFACTOR]
        assert any("unused function" in s.title.lower() for s in refactor)

    def test_analyze_long_functions(self, engine):
        context = {"long_functions": [{"name": "process_data", "lines": 120}]}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        refactor = [s for s in results if s.category == SuggestionCategory.REFACTOR]
        assert any("process_data" in s.title for s in refactor)

    def test_analyze_multiple_rules_fire(self, engine):
        context = {
            "has_tests": False,
            "build_failed": True,
            "build_error": "RuntimeError",
            "todo_count": 3,
            "large_files": [{"name": "x.py", "lines": 600}],
        }
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        categories = {s.category for s in results}
        assert SuggestionCategory.TEST in categories
        assert SuggestionCategory.BUG in categories
        assert SuggestionCategory.REMINDER in categories
        assert SuggestionCategory.REFACTOR in categories

    def test_should_notify_high_confidence(self, engine):
        s = Suggestion(
            id="n1", timestamp=datetime.now(), title="t", description="d",
            confidence=0.8, category=SuggestionCategory.COMMIT,
            priority=SuggestionPriority.MEDIUM,
        )
        result = asyncio.get_event_loop().run_until_complete(engine.should_notify(s))
        assert result is True

    def test_should_notify_dismissed(self, engine):
        s = Suggestion(
            id="n2", timestamp=datetime.now(), title="t", description="d",
            confidence=0.9, category=SuggestionCategory.COMMIT,
            priority=SuggestionPriority.MEDIUM, dismissed=True,
        )
        result = asyncio.get_event_loop().run_until_complete(engine.should_notify(s))
        assert result is False

    def test_should_notify_low_confidence(self, engine):
        s = Suggestion(
            id="n3", timestamp=datetime.now(), title="t", description="d",
            confidence=0.1, category=SuggestionCategory.COMMIT,
            priority=SuggestionPriority.LOW, auto_dismiss_threshold=0.3,
        )
        result = asyncio.get_event_loop().run_until_complete(engine.should_notify(s))
        assert result is False

    def test_dismiss(self, engine):
        context = {"has_tests": False}
        results = asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        sid = results[0].id
        asyncio.get_event_loop().run_until_complete(engine.dismiss(sid))
        active = asyncio.get_event_loop().run_until_complete(engine.get_suggestions())
        assert all(s.id != sid for s in active)

    def test_get_stats(self, engine):
        context = {"has_tests": False}
        asyncio.get_event_loop().run_until_complete(engine.analyze(context, []))
        stats = asyncio.get_event_loop().run_until_complete(engine.get_stats())
        assert stats["total_generated"] >= 1
        assert "by_category" in stats

    def test_get_suggestions_sorted_by_time(self, engine):
        context1 = {"has_tests": False}
        asyncio.get_event_loop().run_until_complete(engine.analyze(context1, []))
        context2 = {"todo_count": 5}
        asyncio.get_event_loop().run_until_complete(engine.analyze(context2, []))
        suggs = asyncio.get_event_loop().run_until_complete(engine.get_suggestions())
        assert len(suggs) >= 2
        for i in range(len(suggs) - 1):
            assert suggs[i].timestamp >= suggs[i + 1].timestamp
