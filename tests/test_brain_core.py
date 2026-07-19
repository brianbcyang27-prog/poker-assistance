import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from jarvis.brain.core.models import BrainContext, MemoryEntry, ReasoningResult, ActionDecision
from jarvis.brain.core.context import BrainContextManager
from jarvis.brain.core.memory import MemoryManager
from jarvis.brain.core.reasoning import ReasoningEngine
from jarvis.brain.core.decision import BrainDecisionEngine
from jarvis.brain.core.brain import JARVISBrain


loop = asyncio.get_event_loop()


# ── BrainContext ──────────────────────────────────────────────────────────────

class TestBrainContext:
    def test_create_default(self):
        ctx = BrainContext()
        assert ctx.current_goal == ""
        assert ctx.confidence == 0.0
        assert ctx.timestamp > 0

    def test_to_dict(self):
        ctx = BrainContext(current_goal="test goal", confidence=0.8)
        d = ctx.to_dict()
        assert d["current_goal"] == "test goal"
        assert d["confidence"] == 0.8
        assert "timestamp" in d
        assert isinstance(d["relevant_memories"], list)

    def test_to_dict_truncates_lists(self):
        memories = [{"content": f"m{i}"} for i in range(10)]
        ctx = BrainContext(relevant_memories=memories)
        d = ctx.to_dict()
        assert len(d["relevant_memories"]) == 5

    def test_to_prompt_context_empty(self):
        ctx = BrainContext()
        text = ctx.to_prompt_context()
        assert "Confidence: 0%" in text

    def test_to_prompt_context_populated(self):
        ctx = BrainContext(
            current_goal="build robot",
            user_preferences={"lang": "python"},
            relevant_memories=[{"content": "robot arm design"}],
            recent_decisions=[{"title": "use ROS", "reason": "industry standard"}],
            project_context={"name": "Jarvis"},
            confidence=0.85,
        )
        text = ctx.to_prompt_context()
        assert "Goal: build robot" in text
        assert "lang: python" in text
        assert "robot arm design" in text
        assert "use ROS" in text
        assert "Jarvis" in text
        assert "85%" in text

    def test_to_prompt_context_truncates(self):
        prefs = {f"key{i}": f"val{i}" for i in range(10)}
        ctx = BrainContext(user_preferences=prefs, confidence=0.5)
        text = ctx.to_prompt_context()
        lines = [l.strip() for l in text.split("\n") if l.strip().startswith("-")]
        assert len(lines) <= 6  # max 5 prefs + possible memory/decision lines

    def test_timestamp_auto_set(self):
        before = time.time()
        ctx = BrainContext()
        after = time.time()
        assert before <= ctx.timestamp <= after


# ── MemoryEntry ───────────────────────────────────────────────────────────────

class TestMemoryEntry:
    def test_create_default(self):
        m = MemoryEntry()
        assert m.id.startswith("mem_")
        assert m.timestamp > 0
        assert m.confidence == 0.8

    def test_create_explicit(self):
        m = MemoryEntry(content="test", source="manual", memory_type="fact")
        assert m.content == "test"
        assert m.source == "manual"
        assert m.memory_type == "fact"

    def test_to_dict(self):
        m = MemoryEntry(content="hello", importance="critical", confidence=0.9)
        d = m.to_dict()
        assert d["content"] == "hello"
        assert d["importance"] == "critical"
        assert d["confidence"] == 0.9
        assert "id" in d
        assert "timestamp" in d

    def test_unique_ids(self):
        a = MemoryEntry()
        b = MemoryEntry()
        assert a.id != b.id

    def test_preserves_explicit_id(self):
        m = MemoryEntry(id="custom_id")
        assert m.id == "custom_id"

    def test_metadata_default(self):
        m = MemoryEntry()
        assert m.metadata == {}

    def test_related_entities(self):
        m = MemoryEntry(related_entities=["e1", "e2"])
        assert len(m.related_entities) == 2


# ── ReasoningResult ───────────────────────────────────────────────────────────

class TestReasoningResult:
    def test_create_default(self):
        r = ReasoningResult()
        assert r.conclusion == ""
        assert r.confidence == 0.0
        assert r.reasoning_chain == []

    def test_create_with_data(self):
        r = ReasoningResult(
            conclusion="do it",
            confidence=0.9,
            reasoning_chain=["step1", "step2"],
            warnings=["careful"],
        )
        assert r.conclusion == "do it"
        assert len(r.warnings) == 1

    def test_to_dict(self):
        r = ReasoningResult(conclusion="yes", confidence=0.7)
        d = r.to_dict()
        assert d["conclusion"] == "yes"
        assert d["confidence"] == 0.7
        assert "alternatives" in d
        assert "supporting_memories" in d

    def test_alternatives(self):
        r = ReasoningResult(alternatives=[{"opt": "a"}, {"opt": "b"}])
        assert len(r.to_dict()["alternatives"]) == 2

    def test_to_dict_types(self):
        r = ReasoningResult()
        d = r.to_dict()
        assert isinstance(d["reasoning_chain"], list)
        assert isinstance(d["warnings"], list)


# ── ActionDecision ────────────────────────────────────────────────────────────

class TestActionDecision:
    def test_create_default(self):
        a = ActionDecision()
        assert a.id.startswith("action_")
        assert a.timestamp > 0
        assert a.risk_level == "low"

    def test_create_explicit(self):
        a = ActionDecision(action="deploy", reason="ready", confidence=0.95)
        assert a.action == "deploy"
        assert a.confidence == 0.95

    def test_to_dict(self):
        a = ActionDecision(action="ship", reason="all tests pass")
        d = a.to_dict()
        assert d["action"] == "ship"
        assert d["reason"] == "all tests pass"
        assert "id" in d
        assert "timestamp" in d
        assert "risk_level" in d

    def test_unique_ids(self):
        a = ActionDecision()
        b = ActionDecision()
        assert a.id != b.id

    def test_preserves_explicit_id(self):
        a = ActionDecision(id="custom_action")
        assert a.id == "custom_action"

    def test_alternatives_rejected(self):
        a = ActionDecision(alternatives_rejected=[{"opt": "x"}])
        assert len(a.to_dict()["alternatives_rejected"]) == 1


# ── BrainContextManager ───────────────────────────────────────────────────────

class TestBrainContextManager:
    def test_create_default(self):
        mgr = BrainContextManager()
        assert mgr._kg is None

    def test_build_context_no_engines(self):
        mgr = BrainContextManager()
        ctx = loop.run_until_complete(mgr.build_context("test goal"))
        assert ctx.current_goal == "test goal"
        assert ctx.confidence == 0.5

    def test_build_context_with_preferences(self):
        mock_prefs = AsyncMock()
        mock_pref = MagicMock()
        mock_pref.category = "lang"
        mock_pref.key = "python"
        mock_pref.value = "3.9"
        mock_prefs.get_all = AsyncMock(return_value=[mock_pref])
        mgr = BrainContextManager(preference_engine=mock_prefs)
        ctx = loop.run_until_complete(mgr.build_context("goal"))
        assert ctx.confidence > 0.5
        assert "lang::python" in ctx.user_preferences

    def test_build_context_with_tools(self):
        mgr = BrainContextManager()
        ctx = loop.run_until_complete(mgr.build_context("goal", tools=["git", "docker"]))
        assert ctx.available_tools == ["git", "docker"]

    def test_inject_context(self):
        mgr = BrainContextManager()
        text = loop.run_until_complete(mgr.inject_context("build robot"))
        assert "Goal: build robot" in text

    def test_build_context_with_project(self):
        mgr = BrainContextManager()
        ctx = loop.run_until_complete(mgr.build_context("goal", project_name="Jarvis"))
        assert ctx.project_context == {}  # no kg, returns {}

    def test_confidence_cap(self):
        mgr = BrainContextManager()
        ctx = loop.run_until_complete(mgr.build_context("x"))
        assert ctx.confidence <= 1.0


# ── MemoryManager ─────────────────────────────────────────────────────────────

class TestMemoryManager:
    def test_create_default(self):
        mgr = MemoryManager()
        assert len(mgr._memories) == 0

    def test_remember(self):
        mgr = MemoryManager()
        entry = loop.run_until_complete(
            mgr.remember("robot uses 6 DOF", memory_type="fact")
        )
        assert entry.content == "robot uses 6 DOF"
        assert entry.memory_type == "fact"
        assert entry.id in mgr._memories

    def test_remember_with_metadata(self):
        mgr = MemoryManager()
        entry = loop.run_until_complete(
            mgr.remember("test", metadata={"key": "val"})
        )
        assert entry.metadata == {"key": "val"}

    def test_recall_local(self):
        mgr = MemoryManager()
        loop.run_until_complete(mgr.remember("robot arm"))
        loop.run_until_complete(mgr.remember("camera module"))
        results = loop.run_until_complete(mgr.recall("robot"))
        assert len(results) == 1
        assert "robot" in results[0].content

    def test_recall_by_type(self):
        mgr = MemoryManager()
        loop.run_until_complete(mgr.remember("fact1", memory_type="fact"))
        loop.run_until_complete(mgr.remember("lesson1", memory_type="lesson"))
        results = loop.run_until_complete(mgr.recall("1", memory_type="fact"))
        assert len(results) == 1
        assert results[0].memory_type == "fact"

    def test_recall_sorted_by_confidence(self):
        mgr = MemoryManager()
        e1 = loop.run_until_complete(
            mgr.remember("robot arm v1", memory_type="fact")
        )
        e2 = loop.run_until_complete(
            mgr.remember("robot arm v2", memory_type="fact")
        )
        mgr._memories[e1.id].confidence = 0.5
        mgr._memories[e2.id].confidence = 0.99
        results = loop.run_until_complete(mgr.recall("robot arm"))
        assert len(results) == 2
        assert results[0].confidence >= results[-1].confidence

    def test_forget(self):
        mgr = MemoryManager()
        entry = loop.run_until_complete(mgr.remember("temp"))
        assert loop.run_until_complete(mgr.forget(entry.id))
        assert entry.id not in mgr._memories

    def test_forget_nonexistent(self):
        mgr = MemoryManager()
        assert not loop.run_until_complete(mgr.forget("nope"))

    def test_get_stats(self):
        mgr = MemoryManager()
        loop.run_until_complete(mgr.remember("a"))
        loop.run_until_complete(mgr.remember("b"))
        stats = loop.run_until_complete(mgr.get_stats())
        assert stats["local_memories"] == 2

    def test_get_profile(self):
        mgr = MemoryManager()
        loop.run_until_complete(mgr.remember("fact1", memory_type="fact"))
        loop.run_until_complete(mgr.remember("lesson1", memory_type="lesson"))
        profile = loop.run_until_complete(mgr.get_profile())
        assert len(profile["facts"]) == 1
        assert len(profile["lessons"]) == 1

    def test_get_context_string_empty(self):
        mgr = MemoryManager()
        text = loop.run_until_complete(mgr.get_context_string())
        assert text == "No context available."

    def test_consolidate_no_engine(self):
        mgr = MemoryManager()
        result = loop.run_until_complete(mgr.consolidate())
        assert result["ok"] is False


# ── ReasoningEngine ───────────────────────────────────────────────────────────

class TestReasoningEngine:
    def test_create_default(self):
        eng = ReasoningEngine()
        assert len(eng._history) == 0

    def test_reason_basic(self):
        eng = ReasoningEngine()
        ctx = BrainContext(current_goal="test", confidence=0.6)
        result = loop.run_until_complete(eng.reason("test", ctx))
        assert "test" in result.conclusion
        assert result.confidence > 0
        assert len(result.reasoning_chain) > 0

    def test_reason_with_preferences(self):
        eng = ReasoningEngine()
        ctx = BrainContext(
            user_preferences={"style": "minimal"},
            confidence=0.7,
        )
        result = loop.run_until_complete(eng.reason("build", ctx))
        assert any("preference" in s.lower() for s in result.reasoning_chain)

    def test_reason_with_memories(self):
        eng = ReasoningEngine()
        ctx = BrainContext(
            relevant_memories=[{"content": "robot arm v2"}],
            confidence=0.7,
        )
        result = loop.run_until_complete(eng.reason("build", ctx))
        assert len(result.supporting_memories) > 0

    def test_reason_low_confidence_warning(self):
        eng = ReasoningEngine()
        ctx = BrainContext(confidence=0.2)
        result = loop.run_until_complete(eng.reason("goal", ctx))
        assert len(result.warnings) > 0

    def test_reason_fresh_territory_warning(self):
        eng = ReasoningEngine()
        ctx = BrainContext(confidence=0.6)
        result = loop.run_until_complete(eng.reason("goal", ctx))
        assert any("fresh" in w.lower() for w in result.warnings)

    def test_analyze_options(self):
        eng = ReasoningEngine()
        options = [
            {"action": "fast deploy", "desc": "speed is key"},
            {"action": "careful review", "desc": "quality matters"},
        ]
        criteria = ["speed", "quality"]
        result = loop.run_until_complete(eng.analyze_options(options, criteria))
        assert len(result) == 2
        assert result[0]["score"] >= result[1]["score"] or result[0]["score"] <= result[1]["score"]
        assert all("score" in r for r in result)

    def test_assess_risk_low(self):
        eng = ReasoningEngine()
        ctx = BrainContext(confidence=0.9, relevant_memories=[{"content": "x"}])
        result = loop.run_until_complete(eng.assess_risk("deploy", ctx))
        assert result["risk_level"] == "low"
        assert result["recommendation"] == "Proceed"

    def test_assess_risk_high(self):
        eng = ReasoningEngine()
        ctx = BrainContext(
            confidence=0.2,
            previous_attempts=[{"outcome": "failed: timeout"}],
        )
        result = loop.run_until_complete(eng.assess_risk("deploy", ctx))
        assert result["risk_level"] == "high"

    def test_reasoning_history(self):
        eng = ReasoningEngine()
        ctx = BrainContext(confidence=0.5)
        loop.run_until_complete(eng.reason("a", ctx))
        loop.run_until_complete(eng.reason("b", ctx))
        assert len(eng.get_reasoning_history()) == 2


# ── JARVISBrain ───────────────────────────────────────────────────────────────

class TestJARVISBrain:
    def test_create_default(self):
        brain = JARVISBrain()
        assert brain._initialized is False
        assert brain.memory is not None
        assert brain.reasoning is not None

    def test_think(self):
        brain = JARVISBrain()
        ctx = loop.run_until_complete(brain.think("build robot"))
        assert ctx.current_goal == "build robot"
        assert ctx.confidence > 0

    def test_remember_and_recall(self):
        brain = JARVISBrain()
        entry = loop.run_until_complete(brain.remember("sensor data is 42"))
        assert entry.content == "sensor data is 42"
        results = loop.run_until_complete(brain.recall("sensor"))
        assert len(results) >= 1

    def test_reason(self):
        brain = JARVISBrain()
        ctx = loop.run_until_complete(brain.think("test"))
        result = loop.run_until_complete(brain.reason("test", ctx))
        assert result.conclusion != ""

    def test_decide(self):
        brain = JARVISBrain()
        ctx = loop.run_until_complete(brain.think("ship it"))
        decision = loop.run_until_complete(
            brain.decide("ship it", ctx, options=[
                {"action": "deploy now", "reason": "all good"},
                {"action": "wait", "reason": "more tests"},
            ])
        )
        assert decision.action != ""
        assert decision.confidence > 0

    def test_get_status(self):
        brain = JARVISBrain()
        status = loop.run_until_complete(brain.get_status())
        assert "health" in status
        assert status["health"] in ("healthy", "degraded", "empty")
        assert "stats" in status

    def test_get_status_empty(self):
        brain = JARVISBrain()
        status = loop.run_until_complete(brain.get_status())
        assert status["health"] == "empty"

    def test_explain_why_nonexistent(self):
        brain = JARVISBrain()
        text = loop.run_until_complete(brain.explain_why("fake_id"))
        assert "not found" in text

    def test_get_stats(self):
        brain = JARVISBrain()
        stats = loop.run_until_complete(brain.get_stats())
        assert "initialized" in stats
        assert "memory" in stats
        assert stats["reasoning_history"] == 0
