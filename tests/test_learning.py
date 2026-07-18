"""Tests for JARVIS Continuous Learning Engine (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.learning import LearningEngine, LearningRecord, SkillUpdate


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestLearningModels:
    def test_learning_record(self):
        record = LearningRecord(
            mission_id="m1",
            libraries_discovered=["fastapi", "pydantic"],
            patterns_learned=["async_api", "dependency_injection"],
            mistakes=["forgot to handle edge case"],
            speed_improvements=["use caching"],
            skill_suggestions=["web_api_design"],
            knowledge_updates=["fastapi is good for async"],
        )
        assert record.mission_id == "m1"
        assert len(record.libraries_discovered) == 2
        assert "fastapi" in record.libraries_discovered

    def test_skill_update(self):
        update = SkillUpdate(
            skill_name="web_api_design",
            description="Design REST APIs",
            before=None,
            after="Use FastAPI with dependency injection",
            reason="Repeated pattern",
            confidence=0.8,
        )
        assert update.skill_name == "web_api_design"
        assert update.confidence == 0.8


# ════════════════════════════════════════════════════════════
# Engine Tests
# ════════════════════════════════════════════════════════════

class TestLearningEngine:
    def setup_method(self):
        self.engine = LearningEngine()

    def test_analyze_mission(self):
        mission_data = {
            "mission_id": "test_mission_1",
            "libraries_used": ["requests", "beautifulsoup4"],
            "actions": [
                {"type": "research", "tool": "github", "reusable": True, "skill_name": "github_search"},
                {"type": "execute", "tool": "python", "failed": True, "error": "ImportError"},
            ],
            "plan": ["research_libraries", "create_project"],
            "findings": ["requests is the best HTTP library"],
        }
        record = _run(self.engine.analyze_mission(mission_data))
        assert isinstance(record, LearningRecord)
        assert record.mission_id == "test_mission_1"
        assert "requests" in record.libraries_discovered
        assert len(record.patterns_learned) > 0
        assert len(record.mistakes) > 0

    def test_extract_patterns(self):
        missions = [
            {
                "mission_id": "m1",
                "actions": [
                    {"type": "research", "tool": "github"},
                    {"type": "execute", "tool": "python"},
                ],
            },
            {
                "mission_id": "m2",
                "actions": [
                    {"type": "research", "tool": "github"},
                    {"type": "execute", "tool": "python"},
                ],
            },
        ]
        patterns = _run(self.engine.extract_patterns(missions))
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        for p in patterns:
            assert p["occurrence_count"] >= 2

    def test_suggest_skill(self):
        mission_data = {
            "mission_id": "m1",
            "actions": [{"reusable": True, "skill_name": "web_scraping"}],
            "suggested_skills": ["data_analysis"],
        }
        skill = _run(self.engine.suggest_skill(mission_data))
        assert isinstance(skill, SkillUpdate)
        assert skill.skill_name in ("web_scraping", "data_analysis")

    def test_suggest_skill_none(self):
        mission_data = {"mission_id": "m1", "actions": []}
        skill = _run(self.engine.suggest_skill(mission_data))
        assert skill is None

    def test_update_knowledge_base(self):
        record = LearningRecord(
            mission_id="m1", libraries_discovered=[], patterns_learned=[],
            mistakes=[], speed_improvements=[], skill_suggestions=[],
            knowledge_updates=[],
        )
        _run(self.engine.update_knowledge_base(record))
        assert len(self.engine._knowledge_base) == 1
        # Duplicate should not be added
        _run(self.engine.update_knowledge_base(record))
        assert len(self.engine._knowledge_base) == 1

    def test_get_recommendations(self):
        record = LearningRecord(
            mission_id="m1",
            libraries_discovered=["fastapi"],
            patterns_learned=["async web api development"],
            mistakes=["forgot error handling"],
            speed_improvements=[], skill_suggestions=[],
            knowledge_updates=[],
        )
        _run(self.engine.update_knowledge_base(record))
        recs = _run(self.engine.get_recommendations("build a web api with fastapi"))
        assert isinstance(recs, list)

    def test_improve_skill(self):
        mission_data = {
            "mission_id": "m1",
            "actions": [{"optimization": "Use connection pooling"}],
        }
        update = _run(self.engine.improve_skill("http_client", mission_data))
        assert isinstance(update, SkillUpdate)
        assert update.skill_name == "http_client"
        assert update.before is None

    def test_improve_skill_with_existing(self):
        # First create
        _run(self.engine.improve_skill("caching", {"mission_id": "m1", "actions": []}))
        # Then improve
        update = _run(self.engine.improve_skill("caching", {"mission_id": "m2", "actions": [{"optimization": "Use Redis"}]}))
        assert update.before is not None

    def test_mission_without_id(self):
        mission_data = {
            "libraries_used": ["torch"],
            "actions": [{"type": "train", "tool": "pytorch"}],
        }
        record = _run(self.engine.analyze_mission(mission_data))
        assert record.mission_id != ""
