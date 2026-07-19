"""Tests for jarvis.consolidation — models and ConsolidationEngine."""

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.consolidation.models import (
    ConsolidationAction,
    ConsolidationResult,
    DuplicateGroup,
    MergeCandidate,
)
from jarvis.consolidation.engine import ConsolidationEngine


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Mock knowledge graph — satisfies the interface ConsolidationEngine expects
# ---------------------------------------------------------------------------
class MockKG:
    """In-memory SQLite graph compatible with ConsolidationEngine."""

    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                label TEXT,
                type TEXT DEFAULT 'concept',
                content TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS edges (
                source TEXT,
                target TEXT,
                relation TEXT DEFAULT 'related_to',
                weight REAL DEFAULT 1.0,
                metadata TEXT DEFAULT '{}',
                created_at REAL DEFAULT 0
            );
        """)
        self._conn.commit()

    def _get_conn(self):
        return self._conn

    async def add_node(self, node):
        self._conn.execute(
            "INSERT OR REPLACE INTO nodes (id,label,type,content,metadata,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (
                node.id,
                node.label,
                node.type,
                node.content,
                node.metadata,
                getattr(node, "created_at", 0) or 0,
                getattr(node, "updated_at", 0) or 0,
            ),
        )
        self._conn.commit()
        return {"ok": True}

    async def get_node(self, node_id):
        row = self._conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        return dict(row) if row else None

    async def add_edge(self, edge):
        self._conn.execute(
            "INSERT OR REPLACE INTO edges (source,target,relation,weight,metadata,created_at) VALUES (?,?,?,?,?,?)",
            (edge.source, edge.target, edge.relation, edge.weight, edge.metadata, time.time()),
        )
        self._conn.commit()
        return {"ok": True}

    async def get_neighbors(self, node_id):
        outgoing_rows = self._conn.execute("SELECT * FROM edges WHERE source=?", (node_id,)).fetchall()
        incoming_rows = self._conn.execute("SELECT * FROM edges WHERE target=?", (node_id,)).fetchall()
        return {
            "neighbors": {
                "outgoing": [dict(r) for r in outgoing_rows],
                "incoming": [dict(r) for r in incoming_rows],
            }
        }

    async def get_graph_data(self, limit=10000):
        rows = self._conn.execute("SELECT * FROM nodes LIMIT ?", (limit,)).fetchall()
        return {"nodes": [dict(r) for r in rows]}

    async def get_stats(self):
        nodes = self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edges = self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        return {"nodes": nodes, "edges": edges, "notes": 0, "types": {}}


class _Node:
    def __init__(self, id, label="", type="concept", content="", metadata="{}", created_at=0, updated_at=0):
        self.id = id
        self.label = label
        self.type = type
        self.content = content
        self.metadata = metadata
        self.created_at = created_at
        self.updated_at = updated_at


class _Edge:
    def __init__(self, source="", target="", relation="related_to", weight=1.0, metadata="{}"):
        self.source = source
        self.target = target
        self.relation = relation
        self.weight = weight
        self.metadata = metadata


# Patch the engine's import so it resolves Node/Edge from our mocks
import jarvis.consolidation.engine as _eng_mod

_orig_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__


def _patched_import(name, *args, **kwargs):
    if name == "jarvis.brain.memory.graph":
        import types
        mod = types.ModuleType("jarvis.brain.memory.graph")
        mod.Node = _Node
        mod.Edge = _Edge
        return mod
    return _orig_import(name, *args, **kwargs)


# ---------------------------------------------------------------------------
# TestConsolidationModels
# ---------------------------------------------------------------------------
class TestConsolidationModels:
    def test_consolidation_result_defaults(self):
        r = ConsolidationResult()
        assert r.actions_taken == []
        assert r.duplicates_removed == 0
        assert r.memories_merged == 0
        assert r.memories_strengthened == 0
        assert r.memories_summarized == 0
        assert r.memories_forgotten == 0
        assert r.timestamp > 0

    def test_consolidation_result_to_dict(self):
        r = ConsolidationResult(
            actions_taken=[{"action": "merge"}, {"action": "forget"}],
            duplicates_removed=3,
            memories_merged=2,
            memories_strengthened=5,
            memories_summarized=1,
            memories_forgotten=4,
        )
        d = r.to_dict()
        assert d["actions_taken"] == 2
        assert d["duplicates_removed"] == 3
        assert d["memories_merged"] == 2
        assert d["memories_strengthened"] == 5
        assert d["memories_summarized"] == 1
        assert d["memories_forgotten"] == 4
        assert "timestamp" in d

    def test_duplicate_group_defaults(self):
        dg = DuplicateGroup()
        assert dg.entity_ids == []
        assert dg.reason == ""
        assert dg.confidence == 0.0

    def test_duplicate_group_to_dict(self):
        dg = DuplicateGroup(entity_ids=["a", "b"], reason="same label", confidence=0.95)
        d = dg.to_dict()
        assert d["entity_ids"] == ["a", "b"]
        assert d["reason"] == "same label"
        assert d["confidence"] == 0.95

    def test_merge_candidate_defaults(self):
        mc = MergeCandidate()
        assert mc.primary_id == ""
        assert mc.secondary_id == ""
        assert mc.reason == ""
        assert mc.combined_data == {}

    def test_merge_candidate_to_dict(self):
        mc = MergeCandidate(
            primary_id="p1",
            secondary_id="p2",
            reason="overlap",
            combined_data={"content": "merged"},
        )
        d = mc.to_dict()
        assert d["primary_id"] == "p1"
        assert d["secondary_id"] == "p2"
        assert d["reason"] == "overlap"
        assert d["combined_data"] == {"content": "merged"}

    def test_consolidation_action_values(self):
        assert ConsolidationAction.DEDUPLICATE.value == "deduplicate"
        assert ConsolidationAction.MERGE.value == "merge"
        assert ConsolidationAction.STRENGTHEN.value == "strengthen"
        assert ConsolidationAction.SUMMARIZE.value == "summarize"
        assert ConsolidationAction.FORGET.value == "forget"


# ---------------------------------------------------------------------------
# TestConsolidationEngine
# ---------------------------------------------------------------------------
class TestConsolidationEngine:
    def _make_engine(self):
        kg = MockKG()
        return ConsolidationEngine(knowledge_graph=kg), kg

    def _seed(self, kg, nodes, edges=None):
        """Populate MockKG with _Node and _Edge objects."""
        for n in nodes:
            _run(kg.add_node(n))
        for e in (edges or []):
            _run(kg.add_edge(e))

    def _make_node(self, id, label=None, content="", confidence=0.7, created_at=0):
        label = label or id
        meta = json.dumps({"confidence": confidence})
        return _Node(id=id, label=label, content=content, metadata=meta, created_at=created_at, updated_at=time.time())

    def test_find_duplicates_found(self):
        eng, kg = self._make_engine()
        self._seed(kg, [
            self._make_node("n1", label="python"),
            self._make_node("n2", label="python"),
        ])
        dupes = _run(eng.find_duplicates())
        assert len(dupes) == 1
        assert len(dupes[0].entity_ids) == 2
        assert dupes[0].confidence == 0.95

    def test_find_duplicates_none(self):
        eng, kg = self._make_engine()
        self._seed(kg, [
            self._make_node("n1", label="python"),
            self._make_node("n2", label="rust"),
        ])
        dupes = _run(eng.find_duplicates())
        assert len(dupes) == 0

    def test_merge_entities(self):
        eng, kg = self._make_engine()
        self._seed(
            kg,
            [
                self._make_node("p1", label="primary", content="primary content."),
                self._make_node("s1", label="secondary", content="secondary content"),
            ],
            [_Edge(source="s1", target="other", relation="related_to")],
        )
        result = _run(eng.merge("p1", "s1"))
        assert result["ok"] is True
        assert result["merged"] == "s1"
        assert result["into"] == "p1"
        primary = _run(kg.get_node("p1"))
        assert "secondary content" in primary["content"]

    def test_merge_nonexistent_returns_error(self):
        eng, kg = self._make_engine()
        result = _run(eng.merge("missing1", "missing2"))
        assert result["ok"] is False

    def test_deduplicate(self):
        eng, kg = self._make_engine()
        self._seed(kg, [
            self._make_node("d1", label="dup"),
            self._make_node("d2", label="dup"),
            self._make_node("d3", label="unique"),
        ])
        removed = _run(eng.deduplicate())
        assert removed >= 1
        primary = _run(kg.get_node("d1"))
        assert primary is not None

    def test_strengthen_recent(self):
        eng, kg = self._make_engine()
        now = time.time()
        self._seed(kg, [
            self._make_node("r1", label="recent", confidence=0.5, created_at=now),
            self._make_node("r2", label="old", confidence=0.5, created_at=now - 86400 * 10),
        ])
        count = _run(eng.strengthen_recent(hours=24, delta=0.2))
        assert count == 1
        node = _run(kg.get_node("r1"))
        meta = json.loads(node["metadata"])
        assert meta["confidence"] == 0.7

    def test_forget_weak(self):
        eng, kg = self._make_engine()
        self._seed(kg, [
            self._make_node("w1", label="weak", confidence=0.1),
            self._make_node("w2", label="strong", confidence=0.9),
        ])
        forgotten = _run(eng.forget_weak(threshold=0.2))
        assert forgotten == 1
        node = _run(kg.get_node("w1"))
        assert node is None
        node2 = _run(kg.get_node("w2"))
        assert node2 is not None

    def test_forget_weak_none_below_threshold(self):
        eng, kg = self._make_engine()
        self._seed(kg, [
            self._make_node("k1", label="ok", confidence=0.5),
        ])
        forgotten = _run(eng.forget_weak(threshold=0.2))
        assert forgotten == 0

    def test_summarize_cluster(self):
        eng, kg = self._make_engine()
        self._seed(kg, [
            self._make_node("c1", label="alpha", content="Alpha content here"),
            self._make_node("c2", label="beta", content="Beta content here"),
        ])
        summary = _run(eng.summarize_cluster(["c1", "c2"]))
        assert "alpha" in summary
        assert "Alpha content here" in summary
        assert "beta" in summary

    def test_summarize_cluster_empty(self):
        eng, kg = self._make_engine()
        summary = _run(eng.summarize_cluster([]))
        assert summary == ""

    def test_get_stats(self):
        eng, kg = self._make_engine()
        self._seed(kg, [
            self._make_node("s1", label="a"),
            self._make_node("s2", label="b"),
        ], [_Edge(source="s1", target="s2")])
        stats = _run(eng.get_stats())
        assert stats["ok"] is True
        assert stats["nodes"] == 2
        assert stats["edges"] == 1

    def test_consolidate_full_cycle(self):
        eng, kg = self._make_engine()
        now = time.time()
        self._seed(kg, [
            self._make_node("fc1", label="dup1", confidence=0.8, created_at=now),
            self._make_node("fc2", label="dup1", confidence=0.8, created_at=now),
            self._make_node("fc3", label="weak", confidence=0.1, created_at=now - 86400 * 200),
        ])
        result = _run(eng.consolidate())
        assert isinstance(result, ConsolidationResult)
        assert result.memories_merged >= 1
        assert result.memories_forgotten >= 1
        assert len(result.actions_taken) >= 1
