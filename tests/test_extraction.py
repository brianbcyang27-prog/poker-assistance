"""Tests for jarvis.extraction — models, MemoryExtractor."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.extraction.models import (
    ExtractedType,
    ImportanceLevel,
    ExtractionResult,
    ExtractedMemory,
)
from jarvis.extraction.extractor import MemoryExtractor


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# TestExtractionModels
# ---------------------------------------------------------------------------
class TestExtractionModels:
    def test_extraction_result_defaults(self):
        r = ExtractionResult()
        assert r.source_text == ""
        assert r.extracted_items == []
        assert r.entities_created == []
        assert r.relationships_created == []
        assert r.timestamp > 0

    def test_extraction_result_to_dict(self):
        r = ExtractionResult(
            source_text="hello world " * 30,
            extracted_items=[{"a": 1}, {"b": 2}],
            entities_created=["e1"],
            relationships_created=["e1->e2"],
        )
        d = r.to_dict()
        assert d["extracted_count"] == 2
        assert d["entities_created"] == ["e1"]
        assert d["relationships_created"] == ["e1->e2"]
        assert len(d["source_text"]) <= 200

    def test_extracted_memory_defaults(self):
        m = ExtractedMemory()
        assert m.content == ""
        assert m.extracted_type == "fact"
        assert m.importance == "useful"
        assert m.confidence == 0.7
        assert m.source == ""
        assert m.related_entities == []
        assert m.metadata == {}
        assert m.timestamp > 0

    def test_extracted_memory_to_dict(self):
        m = ExtractedMemory(
            content="test content",
            extracted_type=ExtractedType.DECISION.value,
            importance=ImportanceLevel.IMPORTANT.value,
            confidence=0.9,
            source="test_source",
            related_entities=["ent1"],
            metadata={"key": "val"},
        )
        d = m.to_dict()
        assert d["content"] == "test content"
        assert d["extracted_type"] == "decision"
        assert d["importance"] == "important"
        assert d["confidence"] == 0.9
        assert d["source"] == "test_source"
        assert d["related_entities"] == ["ent1"]
        assert d["metadata"] == {"key": "val"}

    def test_extracted_type_values(self):
        assert ExtractedType.FACT.value == "fact"
        assert ExtractedType.DECISION.value == "decision"
        assert ExtractedType.PREFERENCE.value == "preference"
        assert ExtractedType.PROJECT.value == "project"
        assert ExtractedType.TECHNOLOGY.value == "technology"
        assert ExtractedType.PERSON.value == "person"
        assert ExtractedType.LESSON.value == "lesson"
        assert ExtractedType.GOAL.value == "goal"
        assert ExtractedType.TASK.value == "task"
        assert ExtractedType.EVENT.value == "event"

    def test_importance_level_values(self):
        assert ImportanceLevel.TEMPORARY.value == "temporary"
        assert ImportanceLevel.USEFUL.value == "useful"
        assert ImportanceLevel.IMPORTANT.value == "important"
        assert ImportanceLevel.PERMANENT.value == "permanent"


# ---------------------------------------------------------------------------
# TestMemoryExtractor
# ---------------------------------------------------------------------------
class TestMemoryExtractor:
    def _make_extractor(self):
        return MemoryExtractor(knowledge_graph=None)

    def test_extract_from_text_returns_result(self):
        ext = self._make_extractor()
        result = _run(ext.extract_from_text("Just a simple test message"))
        assert isinstance(result, ExtractionResult)
        assert result.source_text == "Just a simple test message"
        assert isinstance(result.extracted_items, list)

    def test_extract_entities_project(self):
        ext = self._make_extractor()
        entities = _run(ext.extract_entities('project "my-project" is active'))
        assert len(entities) >= 1
        assert any(e["entity_type"] == "project" for e in entities)

    def test_extract_entities_technology(self):
        ext = self._make_extractor()
        entities = _run(ext.extract_entities("Using Python for the backend"))
        assert len(entities) >= 1
        assert any(e["entity_type"] == "technology" for e in entities)

    def test_extract_entities_concept(self):
        ext = self._make_extractor()
        entities = _run(ext.extract_entities("We discussed [[machine learning]] today"))
        assert len(entities) >= 1
        concept = next(e for e in entities if e["entity_type"] == "concept")
        assert concept["name"] == "machine learning"

    def test_extract_relationships(self):
        ext = self._make_extractor()
        rels = _run(ext.extract_relationships("The module is a component of the system"))
        assert len(rels) >= 1
        assert rels[0]["relation"] == "depends_on"

    def test_extract_decisions_found(self):
        ext = self._make_extractor()
        decisions = _run(ext.extract_decisions("We decided to use PostgreSQL"))
        assert len(decisions) == 1
        assert decisions[0]["confidence"] > 0

    def test_extract_decisions_none(self):
        ext = self._make_extractor()
        decisions = _run(ext.extract_decisions("The weather is nice today"))
        assert len(decisions) == 0

    def test_extract_preferences_found(self):
        ext = self._make_extractor()
        prefs = _run(ext.extract_preferences("I prefer dark mode over light mode"))
        assert len(prefs) >= 1

    def test_extract_preferences_none(self):
        ext = self._make_extractor()
        prefs = _run(ext.extract_preferences("Database migration completed"))
        assert len(prefs) == 0

    def test_extract_projects(self):
        ext = self._make_extractor()
        projects = _run(ext.extract_projects("Working on the jarvis-project this week"))
        assert len(projects) >= 1
        assert projects[0]["name"].strip() != ""

    def test_extract_technologies(self):
        ext = self._make_extractor()
        techs = _run(ext.extract_technologies("Built with React and PostgreSQL on Docker"))
        assert len(techs) >= 2
        names = {t["name"] for t in techs}
        assert "React" in names
        assert "PostgreSQL" in names

    def test_extract_people_mention(self):
        ext = self._make_extractor()
        people = _run(ext.extract_people("Talked to @alice about the project"))
        assert len(people) >= 1
        assert people[0]["name"] == "alice"

    def test_extract_lessons_found(self):
        ext = self._make_extractor()
        lessons = _run(ext.extract_lessons("I learned that caching improves performance"))
        assert len(lessons) >= 1
        assert lessons[0]["confidence"] > 0

    def test_extract_lessons_none(self):
        ext = self._make_extractor()
        lessons = _run(ext.extract_lessons("Deployed to production at 3pm"))
        assert len(lessons) == 0

    def test_classify_importance_permanent(self):
        ext = self._make_extractor()
        level = _run(ext.classify_importance("This is a critical requirement"))
        assert level == ImportanceLevel.PERMANENT

    def test_classify_important_decision(self):
        ext = self._make_extractor()
        level = _run(ext.classify_importance("We decided to switch frameworks"))
        assert level == ImportanceLevel.IMPORTANT

    def test_classify_important_project(self):
        ext = self._make_extractor()
        level = _run(ext.classify_importance("Building a new project for the team"))
        assert level == ImportanceLevel.IMPORTANT

    def test_classify_temporary(self):
        ext = self._make_extractor()
        level = _run(ext.classify_importance("ok done"))
        assert level == ImportanceLevel.TEMPORARY

    def test_classify_useful(self):
        ext = self._make_extractor()
        level = _run(ext.classify_importance("The database stores user sessions and provides fast access"))
        assert level == ImportanceLevel.USEFUL

    def test_extract_from_text_populates_items(self):
        ext = self._make_extractor()
        text = (
            "We decided to use Python and React for the new project. "
            "Alice recommended PostgreSQL over MongoDB. "
            "Next time we should test more before deploying."
        )
        result = _run(ext.extract_from_text(text))
        assert len(result.extracted_items) > 0
        types = {item["extracted_type"] for item in result.extracted_items}
        assert "decision" in types or "technology" in types or "lesson" in types


# ---------------------------------------------------------------------------
# TestMemoryExtractorWithGraph
# ---------------------------------------------------------------------------
class TestMemoryExtractorWithGraph:
    """Tests using a mock knowledge_graph (validates the integration path)."""

    def test_extractor_with_none_graph(self):
        ext = MemoryExtractor(knowledge_graph=None)
        result = _run(ext.extract_from_text("Using Python for testing"))
        assert isinstance(result, ExtractionResult)
        assert result.entities_created == []

    def test_extractor_with_mock_graph_passes_through(self):
        class MockGraph:
            async def add_node(self, node):
                return {"ok": True}
            async def add_edge(self, edge):
                return {"ok": True}

        ext = MemoryExtractor(knowledge_graph=MockGraph())
        text = 'project "test-proj" using Python and React'
        result = _run(ext.extract_from_text(text))
        assert isinstance(result, ExtractionResult)
        assert len(result.extracted_items) > 0
