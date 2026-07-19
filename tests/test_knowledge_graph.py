"""Tests for jarvis.knowledge — models, KnowledgeGraph, RelationshipEngine."""

import asyncio
import os
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.knowledge.models import (
    Entity,
    Relationship,
    EntityCluster,
    GraphStats,
    EntityType,
    ImportanceLevel,
    RelationType,
)
from jarvis.knowledge.graph import KnowledgeGraph
from jarvis.knowledge.relationships import RelationshipEngine


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _tmp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    f.close()
    return f.name


def _make_entity(**overrides):
    defaults = {
        "name": "test_entity",
        "entity_type": EntityType.CONCEPT.value,
        "description": "A test entity",
        "importance": ImportanceLevel.USEFUL.value,
        "confidence": 0.8,
    }
    defaults.update(overrides)
    return Entity(**defaults)


# ---------------------------------------------------------------------------
# TestEntityModels
# ---------------------------------------------------------------------------
class TestEntityModels:
    def test_create_default_entity(self):
        e = Entity(name="alpha")
        assert e.name == "alpha"
        assert e.entity_type == "concept"
        assert e.importance == "useful"
        assert e.confidence == 0.8
        assert e.source_memories == []
        assert e.metadata == {}
        assert e.id != ""
        assert e.created_at > 0
        assert e.updated_at > 0

    def test_create_entity_each_type(self):
        for et in EntityType:
            e = Entity(name=f"e_{et.value}", entity_type=et.value)
            assert e.entity_type == et.value
            assert e.name == f"e_{et.value}"

    def test_entity_to_dict(self):
        e = Entity(name="obj", entity_type=EntityType.PROJECT.value)
        d = e.to_dict()
        assert d["name"] == "obj"
        assert d["entity_type"] == "project"
        assert "id" in d
        assert "created_at" in d
        assert "updated_at" in d
        assert isinstance(d["source_memories"], list)
        assert isinstance(d["metadata"], dict)

    def test_entity_id_auto_generated(self):
        e1 = Entity(name="a")
        e2 = Entity(name="b")
        assert e1.id != e2.id

    def test_entity_explicit_id(self):
        e = Entity(id="custom_id", name="x")
        assert e.id == "custom_id"

    def test_entity_to_dict_roundtrip_data(self):
        e = Entity(
            name="roundtrip",
            entity_type=EntityType.PERSON.value,
            description="desc",
            importance=ImportanceLevel.PERMANENT.value,
            confidence=0.95,
            source_memories=["mem1"],
            metadata={"key": "val"},
        )
        d = e.to_dict()
        assert d["description"] == "desc"
        assert d["importance"] == "permanent"
        assert d["confidence"] == 0.95
        assert d["source_memories"] == ["mem1"]
        assert d["metadata"] == {"key": "val"}

    def test_entity_default_confidence(self):
        e = Entity(name="c")
        assert e.confidence == 0.8

    def test_entity_importance_level_values(self):
        for imp in ImportanceLevel:
            e = Entity(name=f"i_{imp.value}", importance=imp.value)
            assert e.importance == imp.value


# ---------------------------------------------------------------------------
# TestRelationshipModels
# ---------------------------------------------------------------------------
class TestRelationshipModels:
    def test_create_default_relationship(self):
        r = Relationship(source_id="s", target_id="t")
        assert r.source_id == "s"
        assert r.target_id == "t"
        assert r.relation_type == "related_to"
        assert r.weight == 1.0
        assert r.confidence == 0.8
        assert r.created_at > 0

    def test_create_relationship_each_type(self):
        for rt in RelationType:
            r = Relationship(source_id="a", target_id="b", relation_type=rt.value)
            assert r.relation_type == rt.value

    def test_relationship_to_dict(self):
        r = Relationship(
            source_id="s",
            target_id="t",
            relation_type=RelationType.USES.value,
            weight=3.5,
            description="uses it",
            confidence=0.9,
            metadata={"k": "v"},
        )
        d = r.to_dict()
        assert d["source_id"] == "s"
        assert d["target_id"] == "t"
        assert d["relation_type"] == "uses"
        assert d["weight"] == 3.5
        assert d["description"] == "uses it"
        assert d["confidence"] == 0.9
        assert d["metadata"] == {"k": "v"}
        assert "created_at" in d

    def test_relationship_defaults(self):
        r = Relationship()
        assert r.weight == 1.0
        assert r.description == ""
        assert r.metadata == {}

    def test_entity_cluster_to_dict(self):
        e = Entity(name="cl")
        r = Relationship(source_id="a", target_id="b")
        c = EntityCluster(name="cluster1", entities=[e], relationships=[r], central_entity="a")
        d = c.to_dict()
        assert d["name"] == "cluster1"
        assert len(d["entities"]) == 1
        assert len(d["relationships"]) == 1
        assert d["central_entity"] == "a"

    def test_graph_stats_to_dict(self):
        s = GraphStats(
            total_entities=5,
            total_relationships=3,
            entity_type_counts={"person": 2, "project": 3},
            relationship_type_counts={"uses": 3},
            avg_confidence=0.75,
            avg_importance=2.5,
        )
        d = s.to_dict()
        assert d["total_entities"] == 5
        assert d["total_relationships"] == 3
        assert d["entity_type_counts"]["person"] == 2
        assert d["avg_confidence"] == 0.75

    def test_graph_stats_defaults(self):
        s = GraphStats()
        assert s.total_entities == 0
        assert s.total_relationships == 0
        assert s.entity_type_counts == {}
        assert s.avg_confidence == 0.0


# ---------------------------------------------------------------------------
# TestKnowledgeGraph
# ---------------------------------------------------------------------------
class TestKnowledgeGraph:
    def _make_graph(self):
        db = _tmp_db()
        return KnowledgeGraph(db_path=db)

    def test_add_and_get_entity(self):
        g = self._make_graph()
        e = _make_entity(name="person_a", entity_type=EntityType.PERSON.value)
        _run(g.add_entity(e))
        got = _run(g.get_entity(e.id))
        assert got is not None
        assert got.name == "person_a"
        assert got.entity_type == "person"
        _run(g.close())

    def test_get_entity_not_found(self):
        g = self._make_graph()
        got = _run(g.get_entity("nonexistent"))
        assert got is None
        _run(g.close())

    def test_update_entity(self):
        g = self._make_graph()
        e = _make_entity(name="old_name")
        _run(g.add_entity(e))
        e.name = "new_name"
        e.description = "updated"
        _run(g.update_entity(e))
        got = _run(g.get_entity(e.id))
        assert got.name == "new_name"
        assert got.description == "updated"
        _run(g.close())

    def test_delete_entity(self):
        g = self._make_graph()
        e = _make_entity(name="delete_me")
        _run(g.add_entity(e))
        result = _run(g.delete_entity(e.id))
        assert result["ok"] is True
        got = _run(g.get_entity(e.id))
        assert got is None
        _run(g.close())

    def test_delete_entity_removes_relationships(self):
        g = self._make_graph()
        e1 = _make_entity(name="a")
        e2 = _make_entity(name="b")
        _run(g.add_entity(e1))
        _run(g.add_entity(e2))
        rel = Relationship(source_id=e1.id, target_id=e2.id, relation_type="related_to")
        _run(g.add_relationship(rel))
        _run(g.delete_entity(e1.id))
        rels = _run(g.get_relationships())
        assert len(rels) == 0
        _run(g.close())

    def test_search_entities(self):
        g = self._make_graph()
        _run(g.add_entity(_make_entity(name="python_project", entity_type=EntityType.PROJECT.value)))
        _run(g.add_entity(_make_entity(name="rust_tool", entity_type=EntityType.TECHNOLOGY.value)))
        _run(g.add_entity(_make_entity(name="python_script", entity_type=EntityType.TECHNOLOGY.value)))
        results = _run(g.search_entities("python"))
        assert len(results) == 2
        names = {r.name for r in results}
        assert "python_project" in names
        assert "python_script" in names
        _run(g.close())

    def test_search_entities_with_type_filter(self):
        g = self._make_graph()
        _run(g.add_entity(_make_entity(name="python_proj", entity_type=EntityType.PROJECT.value)))
        _run(g.add_entity(_make_entity(name="python_lang", entity_type=EntityType.TECHNOLOGY.value)))
        results = _run(g.search_entities("python", entity_type="project"))
        assert len(results) == 1
        assert results[0].name == "python_proj"
        _run(g.close())

    def test_get_neighbors(self):
        g = self._make_graph()
        e1 = _make_entity(name="center")
        e2 = _make_entity(name="neighbor1")
        e3 = _make_entity(name="neighbor2")
        _run(g.add_entity(e1))
        _run(g.add_entity(e2))
        _run(g.add_entity(e3))
        _run(g.add_relationship(Relationship(source_id=e1.id, target_id=e2.id)))
        _run(g.add_relationship(Relationship(source_id=e1.id, target_id=e3.id)))
        neighbors = _run(g.get_neighbors(e1.id, depth=1))
        assert len(neighbors["entities"]) >= 2
        _run(g.close())

    def test_get_by_type(self):
        g = self._make_graph()
        _run(g.add_entity(_make_entity(name="p1", entity_type=EntityType.PERSON.value)))
        _run(g.add_entity(_make_entity(name="p2", entity_type=EntityType.PERSON.value)))
        _run(g.add_entity(_make_entity(name="proj1", entity_type=EntityType.PROJECT.value)))
        people = _run(g.get_by_type("person"))
        assert len(people) == 2
        assert all(p.entity_type == "person" for p in people)
        _run(g.close())

    def test_get_by_importance(self):
        g = self._make_graph()
        _run(g.add_entity(_make_entity(name="imp1", importance=ImportanceLevel.IMPORTANT.value)))
        _run(g.add_entity(_make_entity(name="imp2", importance=ImportanceLevel.IMPORTANT.value)))
        _run(g.add_entity(_make_entity(name="temp1", importance=ImportanceLevel.TEMPORARY.value)))
        imps = _run(g.get_by_importance(ImportanceLevel.IMPORTANT.value))
        assert len(imps) == 2
        _run(g.close())

    def test_get_entity_clusters(self):
        g = self._make_graph()
        e1 = _make_entity(name="cluster_a")
        e2 = _make_entity(name="cluster_b")
        _run(g.add_entity(e1))
        _run(g.add_entity(e2))
        _run(g.add_relationship(Relationship(source_id=e1.id, target_id=e2.id, weight=2.0)))
        clusters = _run(g.get_entity_clusters(min_weight=0.5))
        assert len(clusters) >= 1
        _run(g.close())

    def test_get_subgraph(self):
        g = self._make_graph()
        e1 = _make_entity(name="sub1")
        e2 = _make_entity(name="sub2")
        e3 = _make_entity(name="sub3")
        _run(g.add_entity(e1))
        _run(g.add_entity(e2))
        _run(g.add_entity(e3))
        _run(g.add_relationship(Relationship(source_id=e1.id, target_id=e2.id)))
        sub = _run(g.get_subgraph([e1.id, e2.id]))
        assert len(sub["entities"]) == 2
        assert len(sub["relationships"]) == 1
        _run(g.close())

    def test_get_subgraph_empty(self):
        g = self._make_graph()
        sub = _run(g.get_subgraph([]))
        assert sub["entities"] == []
        assert sub["relationships"] == []
        _run(g.close())

    def test_get_stats(self):
        g = self._make_graph()
        e1 = _make_entity(name="s1", entity_type=EntityType.PERSON.value, importance=ImportanceLevel.IMPORTANT.value)
        e2 = _make_entity(name="s2", entity_type=EntityType.PROJECT.value, importance=ImportanceLevel.USEFUL.value)
        _run(g.add_entity(e1))
        _run(g.add_entity(e2))
        _run(g.add_relationship(Relationship(source_id=e1.id, target_id=e2.id, relation_type="related_to")))
        stats = _run(g.get_stats())
        assert stats.total_entities == 2
        assert stats.total_relationships == 1
        assert "person" in stats.entity_type_counts
        assert "related_to" in stats.relationship_type_counts
        assert stats.avg_confidence > 0
        _run(g.close())

    def test_to_dict(self):
        g = self._make_graph()
        _run(g.add_entity(_make_entity(name="d1")))
        d = _run(g.to_dict())
        assert "entities" in d
        assert "relationships" in d
        assert "count" in d
        assert d["count"]["entities"] == 1
        assert d["count"]["relationships"] == 0
        _run(g.close())

    def test_add_and_get_relationships(self):
        g = self._make_graph()
        e1 = _make_entity(name="r1")
        e2 = _make_entity(name="r2")
        _run(g.add_entity(e1))
        _run(g.add_entity(e2))
        rel = Relationship(source_id=e1.id, target_id=e2.id, relation_type="uses", weight=2.5)
        _run(g.add_relationship(rel))
        rels = _run(g.get_relationships(entity_id=e1.id, direction="outgoing"))
        assert len(rels) == 1
        assert rels[0].weight == 2.5
        assert rels[0].relation_type == "uses"
        _run(g.close())

    def test_delete_relationship(self):
        g = self._make_graph()
        e1 = _make_entity(name="dr1")
        e2 = _make_entity(name="dr2")
        _run(g.add_entity(e1))
        _run(g.add_entity(e2))
        _run(g.add_relationship(Relationship(source_id=e1.id, target_id=e2.id, relation_type="contains")))
        result = _run(g.delete_relationship(e1.id, e2.id, "contains"))
        assert result["ok"] is True
        rels = _run(g.get_relationships())
        assert len(rels) == 0
        _run(g.close())

    def test_get_relationships_by_type(self):
        g = self._make_graph()
        e1 = _make_entity(name="rt1")
        e2 = _make_entity(name="rt2")
        _run(g.add_entity(e1))
        _run(g.add_entity(e2))
        _run(g.add_relationship(Relationship(source_id=e1.id, target_id=e2.id, relation_type="uses")))
        _run(g.add_relationship(Relationship(source_id=e1.id, target_id=e2.id, relation_type="depends_on")))
        rels = _run(g.get_relationships(relation_type="uses"))
        assert len(rels) == 1
        assert rels[0].relation_type == "uses"
        _run(g.close())


# ---------------------------------------------------------------------------
# TestRelationshipEngine
# ---------------------------------------------------------------------------
class TestRelationshipEngine:
    def _make_engine(self):
        db = _tmp_db()
        g = KnowledgeGraph(db_path=db)
        return RelationshipEngine(g), g

    def _seed_entities(self, engine, names):
        entities = []
        for name in names:
            e = _make_entity(name=name)
            _run(engine.graph.add_entity(e))
            entities.append(e)
        return entities

    def test_create_relationship(self):
        eng, g = self._make_engine()
        e1, e2 = self._seed_entities(eng, ["a", "b"])
        result = _run(eng.create_relationship(e1.id, e2.id, "uses"))
        assert result["ok"] is True
        _run(g.close())

    def test_find_path_same_node(self):
        eng, g = self._make_engine()
        e1, = self._seed_entities(eng, ["solo"])
        path = _run(eng.find_path(e1.id, e1.id))
        assert path == [e1.id]
        _run(g.close())

    def test_find_path_direct(self):
        eng, g = self._make_engine()
        e1, e2 = self._seed_entities(eng, ["src", "dst"])
        _run(eng.create_relationship(e1.id, e2.id, "leads_to"))
        path = _run(eng.find_path(e1.id, e2.id))
        assert path is not None
        assert path[0] == e1.id
        assert path[-1] == e2.id
        _run(g.close())

    def test_find_path_bfs(self):
        eng, g = self._make_engine()
        e1, e2, e3 = self._seed_entities(eng, ["a", "b", "c"])
        _run(eng.create_relationship(e1.id, e2.id, "related_to"))
        _run(eng.create_relationship(e2.id, e3.id, "related_to"))
        path = _run(eng.find_path(e1.id, e3.id))
        assert path is not None
        assert len(path) == 3
        assert path[0] == e1.id
        assert path[1] == e2.id
        assert path[2] == e3.id
        _run(g.close())

    def test_find_path_no_path(self):
        eng, g = self._make_engine()
        e1, e2 = self._seed_entities(eng, ["iso1", "iso2"])
        path = _run(eng.find_path(e1.id, e2.id))
        assert path is None
        _run(g.close())

    def test_get_cluster(self):
        eng, g = self._make_engine()
        e1, e2, e3 = self._seed_entities(eng, ["hub", "leaf1", "leaf2"])
        _run(eng.create_relationship(e1.id, e2.id))
        _run(eng.create_relationship(e1.id, e3.id))
        cluster = _run(eng.get_cluster(e1.id, depth=2))
        assert cluster["central_entity"] == e1.id
        assert len(cluster["entities"]) >= 1
        assert len(cluster["relationships"]) >= 1
        _run(g.close())

    def test_suggest_relationships(self):
        eng, g = self._make_engine()
        e1 = _make_entity(name="person1", entity_type=EntityType.PERSON.value)
        e2 = _make_entity(name="project1", entity_type=EntityType.PROJECT.value)
        _run(eng.graph.add_entity(e1))
        _run(eng.graph.add_entity(e2))
        suggestions = _run(eng.suggest_relationships(e1.id))
        assert len(suggestions) >= 1
        assert suggestions[0]["entity_id"] == e2.id
        _run(g.close())

    def test_suggest_relationships_unknown_entity(self):
        eng, g = self._make_engine()
        suggestions = _run(eng.suggest_relationships("nonexistent"))
        assert suggestions == []
        _run(g.close())

    def test_strengthen(self):
        eng, g = self._make_engine()
        e1, e2 = self._seed_entities(eng, ["s1", "s2"])
        _run(eng.create_relationship(e1.id, e2.id, weight=1.0))
        result = _run(eng.strengthen(e1.id, e2.id, delta=0.5))
        assert result["ok"] is True
        assert result["updated"] == 1
        rels = _run(g.get_relationships(entity_id=e1.id))
        assert rels[0].weight == 1.5
        _run(g.close())

    def test_weaken(self):
        eng, g = self._make_engine()
        e1, e2 = self._seed_entities(eng, ["w1", "w2"])
        _run(eng.create_relationship(e1.id, e2.id, weight=1.0))
        result = _run(eng.weaken(e1.id, e2.id, delta=0.3))
        assert result["ok"] is True
        assert result["updated"] == 1
        rels = _run(g.get_relationships(entity_id=e1.id))
        assert len(rels) == 1
        assert abs(rels[0].weight - 0.7) < 1e-6
        _run(g.close())

    def test_weaken_auto_delete(self):
        eng, g = self._make_engine()
        e1, e2 = self._seed_entities(eng, ["wd1", "wd2"])
        _run(eng.create_relationship(e1.id, e2.id, weight=0.2))
        result = _run(eng.weaken(e1.id, e2.id, delta=0.5))
        assert result["deleted"] == 1
        rels = _run(g.get_relationships())
        assert len(rels) == 0
        _run(g.close())

    def test_get_strongest(self):
        eng, g = self._make_engine()
        e1, e2, e3 = self._seed_entities(eng, ["strong", "weak", "mid"])
        _run(eng.create_relationship(e1.id, e2.id, weight=1.0))
        _run(eng.create_relationship(e1.id, e3.id, weight=5.0))
        strongest = _run(eng.get_strongest(n=2))
        assert len(strongest) == 2
        assert strongest[0]["weight"] >= strongest[1]["weight"]
        _run(g.close())

    def test_suggest_relationships_excludes_existing(self):
        eng, g = self._make_engine()
        e1 = _make_entity(name="p1", entity_type=EntityType.PERSON.value)
        e2 = _make_entity(name="t1", entity_type=EntityType.TECHNOLOGY.value)
        _run(eng.graph.add_entity(e1))
        _run(eng.graph.add_entity(e2))
        _run(eng.create_relationship(e1.id, e2.id, "uses"))
        suggestions = _run(eng.suggest_relationships(e1.id))
        suggested_ids = [s["entity_id"] for s in suggestions]
        assert e2.id not in suggested_ids
        _run(g.close())
