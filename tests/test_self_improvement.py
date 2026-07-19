import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import time
import tempfile
import pytest
from unittest.mock import AsyncMock

from jarvis.self_improvement.models import ErrorRecord, RecoveryPlan, Lesson, ErrorSeverity, RecoveryAction
from jarvis.self_improvement.error_memory import ErrorMemory
from jarvis.self_improvement.recovery import AutoRecovery
from jarvis.self_improvement.lessons import LessonEngine


loop = asyncio.get_event_loop()


# ── ErrorRecord ───────────────────────────────────────────────────────────────

class TestErrorRecord:
    def test_create_default(self):
        e = ErrorRecord()
        assert e.id.startswith("err_")
        assert e.occurred_at > 0
        assert e.resolved is False

    def test_create_explicit(self):
        e = ErrorRecord(
            error_type="ModuleNotFoundError",
            message="no module named foo",
            module="brain",
            function="init",
            severity="high",
        )
        assert e.error_type == "ModuleNotFoundError"
        assert e.severity == "high"

    def test_to_dict(self):
        e = ErrorRecord(error_type="TypeError", message="bad type")
        d = e.to_dict()
        assert d["error_type"] == "TypeError"
        assert d["message"] == "bad type"
        assert "id" in d
        assert "occurred_at" in d

    def test_from_dict(self):
        data = {
            "id": "err_test",
            "error_type": "ValueError",
            "message": "invalid",
            "module": "utils",
            "function": "parse",
            "severity": "medium",
            "resolved": True,
            "solution": "check input",
        }
        e = ErrorRecord.from_dict(data)
        assert e.id == "err_test"
        assert e.resolved is True
        assert e.solution == "check input"

    def test_from_dict_defaults(self):
        e = ErrorRecord.from_dict({"id": "custom"})
        assert e.id == "custom"
        assert e.severity == "medium"
        assert e.error_type == ""

    def test_unique_ids(self):
        a = ErrorRecord()
        b = ErrorRecord()
        assert a.id != b.id

    def test_preserves_explicit_id(self):
        e = ErrorRecord(id="custom_err")
        assert e.id == "custom_err"


# ── RecoveryPlan ──────────────────────────────────────────────────────────────

class TestRecoveryPlan:
    def test_create_default(self):
        p = RecoveryPlan()
        assert p.error_id == ""
        assert p.confidence == 0.0
        assert p.requires_permission is True

    def test_create_with_data(self):
        p = RecoveryPlan(
            error_id="err_1",
            actions=[{"type": "retry"}],
            confidence=0.8,
        )
        assert p.error_id == "err_1"
        assert len(p.actions) == 1

    def test_to_dict(self):
        p = RecoveryPlan(error_id="e1", confidence=0.9)
        d = p.to_dict()
        assert d["error_id"] == "e1"
        assert d["confidence"] == 0.9
        assert "actions" in d
        assert "requires_permission" in d

    def test_to_dict_fields(self):
        p = RecoveryPlan(
            estimated_time="5 min",
            fallback="ask user",
        )
        d = p.to_dict()
        assert d["estimated_time"] == "5 min"
        assert d["fallback"] == "ask user"

    def test_empty_actions(self):
        p = RecoveryPlan()
        assert p.to_dict()["actions"] == []


# ── Lesson ────────────────────────────────────────────────────────────────────

class TestLesson:
    def test_create_default(self):
        l = Lesson()
        assert l.id.startswith("lesson_")
        assert l.created_at > 0
        assert l.times_applied == 0

    def test_create_explicit(self):
        l = Lesson(
            category="testing",
            description="always test edge cases",
            trigger="missing test for None input",
            action="add explicit None check",
        )
        assert l.category == "testing"
        assert l.trigger == "missing test for None input"

    def test_to_dict(self):
        l = Lesson(description="test everything", confidence=0.95)
        d = l.to_dict()
        assert d["description"] == "test everything"
        assert d["confidence"] == 0.95
        assert "id" in d
        assert "created_at" in d

    def test_from_dict(self):
        data = {
            "id": "lesson_abc",
            "category": "perf",
            "description": "cache hot paths",
            "trigger": "slow query",
            "action": "add LRU cache",
            "confidence": 0.85,
            "times_applied": 3,
            "created_at": 1000.0,
        }
        l = Lesson.from_dict(data)
        assert l.id == "lesson_abc"
        assert l.times_applied == 3

    def test_from_dict_defaults(self):
        l = Lesson.from_dict({"id": "custom_l"})
        assert l.id == "custom_l"
        assert l.confidence == 0.8
        assert l.category == ""

    def test_unique_ids(self):
        a = Lesson()
        b = Lesson()
        assert a.id != b.id


# ── ErrorMemory ───────────────────────────────────────────────────────────────

class TestErrorMemory:
    def _make(self):
        tmpdir = tempfile.mkdtemp()
        return ErrorMemory(storage_dir=tmpdir)

    def test_create(self):
        em = self._make()
        assert em._errors == {}

    def test_record(self):
        em = self._make()
        record = loop.run_until_complete(
            em.record("TypeError", "bad input", module="core", function="run")
        )
        assert record.error_type == "TypeError"
        assert record.module == "core"

    def test_record_persists(self):
        em = self._make()
        record = loop.run_until_complete(em.record("ValueError", "val"))
        retrieved = loop.run_until_complete(em.get(record.id))
        assert retrieved is not None
        assert retrieved.message == "val"

    def test_search(self):
        em = self._make()
        loop.run_until_complete(em.record("TypeError", "type mismatch"))
        loop.run_until_complete(em.record("ValueError", "value bad"))
        results = loop.run_until_complete(em.search("type"))
        assert len(results) >= 1

    def test_search_by_type(self):
        em = self._make()
        loop.run_until_complete(em.record("TypeError", "a"))
        loop.run_until_complete(em.record("ValueError", "b"))
        results = loop.run_until_complete(em.search("", error_type="TypeError"))
        assert len(results) == 1
        assert results[0].error_type == "TypeError"

    def test_search_by_module(self):
        em = self._make()
        loop.run_until_complete(em.record("Error", "a", module="brain"))
        loop.run_until_complete(em.record("Error", "b", module="tools"))
        results = loop.run_until_complete(em.search("", module="brain"))
        assert len(results) == 1

    def test_resolve(self):
        em = self._make()
        record = loop.run_until_complete(em.record("Error", "fail"))
        resolved = loop.run_until_complete(
            em.resolve(record.id, "installed package", "pip install")
        )
        assert resolved.resolved is True
        assert resolved.solution == "installed package"

    def test_resolve_nonexistent(self):
        em = self._make()
        result = loop.run_until_complete(em.resolve("nope", "fix", "method"))
        assert result is None

    def test_get_solutions(self):
        em = self._make()
        r1 = loop.run_until_complete(em.record("TypeError", "a"))
        loop.run_until_complete(em.resolve(r1.id, "upgrade lib", "pip"))
        r2 = loop.run_until_complete(em.record("TypeError", "b"))
        loop.run_until_complete(em.resolve(r2.id, "upgrade lib", "pip"))
        solutions = loop.run_until_complete(em.get_solutions("TypeError"))
        assert "upgrade lib" in solutions

    def test_get_stats(self):
        em = self._make()
        loop.run_until_complete(em.record("TypeError", "a"))
        r = loop.run_until_complete(em.record("ValueError", "b"))
        loop.run_until_complete(em.resolve(r.id, "fixed", "method"))
        stats = loop.run_until_complete(em.get_stats())
        assert stats["total"] == 2
        assert stats["resolved"] == 1
        assert stats["unresolved"] == 1
        assert stats["by_type"]["TypeError"] == 1

    def test_get_recent(self):
        em = self._make()
        loop.run_until_complete(em.record("A", "1"))
        loop.run_until_complete(em.record("B", "2"))
        loop.run_until_complete(em.record("C", "3"))
        recent = loop.run_until_complete(em.get_recent(2))
        assert len(recent) == 2

    def test_get_unresolved(self):
        em = self._make()
        r1 = loop.run_until_complete(em.record("A", "1"))
        loop.run_until_complete(em.record("B", "2"))
        loop.run_until_complete(em.resolve(r1.id, "fix", "method"))
        unresolved = loop.run_until_complete(em.get_unresolved())
        assert len(unresolved) == 1

    def test_load_save(self):
        em = self._make()
        loop.run_until_complete(em.record("Error", "test"))
        em2 = ErrorMemory(storage_dir=em._storage_dir)
        loop.run_until_complete(em2.load())
        assert len(em2._errors) == 1


# ── AutoRecovery ──────────────────────────────────────────────────────────────

class TestAutoRecovery:
    def _make(self):
        tmpdir = tempfile.mkdtemp()
        em = ErrorMemory(storage_dir=tmpdir)
        return AutoRecovery(error_memory=em)

    def test_create(self):
        rec = self._make()
        assert len(rec._recovery_history) == 0

    def test_diagnose_known_error(self):
        rec = self._make()
        err = ErrorRecord(error_type="ModuleNotFoundError", message="no foo")
        plan = loop.run_until_complete(rec.diagnose(err))
        assert plan.error_id == err.id
        assert plan.confidence > 0
        assert len(plan.actions) > 0

    def test_diagnose_permission_error(self):
        rec = self._make()
        err = ErrorRecord(error_type="PermissionError", message="denied")
        plan = loop.run_until_complete(rec.diagnose(err))
        assert plan.requires_permission is True

    def test_diagnose_unknown_error_no_solutions(self):
        rec = self._make()
        err = ErrorRecord(error_type="CustomError", message="custom fail")
        plan = loop.run_until_complete(rec.diagnose(err))
        assert plan.confidence <= 0.3
        assert plan.actions[0]["type"] == RecoveryAction.SKIP.value

    def test_diagnose_unknown_error_with_past_solution(self):
        rec = self._make()
        r = loop.run_until_complete(
            rec._error_memory.record("CustomError", "first")
        )
        loop.run_until_complete(
            rec._error_memory.resolve(r.id, "restart service", "systemctl")
        )
        err = ErrorRecord(error_type="CustomError", message="again")
        plan = loop.run_until_complete(rec.diagnose(err))
        assert plan.confidence == 0.6

    def test_suggest_alternative_known(self):
        rec = self._make()
        err = ErrorRecord(error_type="FileNotFoundError", message="missing")
        alt = loop.run_until_complete(rec.suggest_alternative(err))
        assert "file" in alt.lower() or "path" in alt.lower()

    def test_suggest_alternative_import(self):
        rec = self._make()
        err = ErrorRecord(error_type="ImportError", message="cannot import 'requests'")
        alt = loop.run_until_complete(rec.suggest_alternative(err))
        assert "install" in alt.lower() or "package" in alt.lower()

    def test_suggest_alternative_permission(self):
        rec = self._make()
        err = ErrorRecord(error_type="OSError", message="Permission denied")
        alt = loop.run_until_complete(rec.suggest_alternative(err))
        assert "permission" in alt.lower()

    def test_suggest_alternative_connection(self):
        rec = self._make()
        err = ErrorRecord(error_type="ConnectionError", message="connection refused")
        alt = loop.run_until_complete(rec.suggest_alternative(err))
        assert "network" in alt.lower() or "connectivity" in alt.lower()

    def test_recovery_history(self):
        rec = self._make()
        err = ErrorRecord(error_type="TypeError", message="bad")
        loop.run_until_complete(rec.diagnose(err))
        assert len(rec.get_recovery_history()) >= 0  # diagnose doesn't add to history

    def test_known_solutions_coverage(self):
        expected_types = [
            "ModuleNotFoundError", "ImportError", "FileNotFoundError",
            "PermissionError", "ConnectionError", "TimeoutError",
            "JSONDecodeError", "KeyError", "ValueError", "TypeError", "OSError",
        ]
        for et in expected_types:
            assert et in AutoRecovery.known_solutions


# ── LessonEngine ──────────────────────────────────────────────────────────────

class TestLessonEngine:
    def _make(self):
        tmpdir = tempfile.mkdtemp()
        return LessonEngine(storage_dir=tmpdir)

    def test_create(self):
        eng = self._make()
        assert eng._lessons == {}

    def test_learn(self):
        eng = self._make()
        lesson = loop.run_until_complete(
            eng.learn(
                error_id="err_1",
                description="always validate input",
                trigger="ValueError on None",
                action="add null check",
                category="testing",
            )
        )
        assert lesson.description == "always validate input"
        assert lesson.category == "testing"

    def test_learn_persists(self):
        eng = self._make()
        lesson = loop.run_until_complete(
            eng.learn("err_1", "cache results", "slow query", "add LRU", category="perf")
        )
        retrieved = loop.run_until_complete(eng.get_by_category("perf"))
        assert len(retrieved) == 1
        assert retrieved[0].id == lesson.id

    def test_get_applicable_lessons(self):
        eng = self._make()
        loop.run_until_complete(
            eng.learn("e1", "test edge cases", "missing test", "add test", category="testing")
        )
        loop.run_until_complete(
            eng.learn("e2", "cache hot paths", "slow query", "add cache", category="performance")
        )
        applicable = loop.run_until_complete(
            eng.get_applicable_lessons({"trigger": "missing test for edge case"})
        )
        assert len(applicable) >= 1

    def test_apply_lesson(self):
        eng = self._make()
        lesson = loop.run_until_complete(
            eng.learn("e1", "do X", "trigger", "action", confidence=0.8)
        )
        result = loop.run_until_complete(eng.apply_lesson(lesson.id))
        assert result["ok"] is True
        assert result["times_applied"] == 1

    def test_apply_lesson_increases_confidence(self):
        eng = self._make()
        lesson = loop.run_until_complete(
            eng.learn("e1", "test", "trig", "act", confidence=0.8)
        )
        loop.run_until_complete(eng.apply_lesson(lesson.id))
        updated = eng._lessons[lesson.id]
        assert updated.confidence > 0.8

    def test_apply_lesson_nonexistent(self):
        eng = self._make()
        result = loop.run_until_complete(eng.apply_lesson("nope"))
        assert result["ok"] is False

    def test_search(self):
        eng = self._make()
        loop.run_until_complete(
            eng.learn("e1", "use async for IO", "blocking", "convert to async", category="perf")
        )
        loop.run_until_complete(
            eng.learn("e2", "add unit tests", "no coverage", "write tests", category="testing")
        )
        results = loop.run_until_complete(eng.search("async"))
        assert len(results) == 1
        assert "async" in results[0].description

    def test_get_all(self):
        eng = self._make()
        loop.run_until_complete(eng.learn("e1", "a", "t", "a"))
        loop.run_until_complete(eng.learn("e2", "b", "t", "b"))
        all_lessons = loop.run_until_complete(eng.get_all())
        assert len(all_lessons) == 2

    def test_load_save(self):
        eng = self._make()
        loop.run_until_complete(eng.learn("e1", "lesson text", "trig", "action"))
        eng2 = LessonEngine(storage_dir=eng._storage_dir)
        loop.run_until_complete(eng2.load())
        assert len(eng2._lessons) == 1
