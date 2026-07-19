"""Tests for JARVIS Second Brain search module (v5.4.0)."""

import sys
import os
import asyncio
import tempfile
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.brain.memory.graph import KnowledgeGraph, Node, Edge
from jarvis.second_brain.models import SearchMode, SearchResult, SearchQuery, SearchStats
from jarvis.second_brain.search import SecondBrainSearch


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestSearchModels:
    def test_search_result(self):
        sr = SearchResult(
            id="n1", name="Python", entity_type="concept",
            description="A programming language", score=0.85,
            match_reasons=["Name matches 'python'"],
            related_entities=["n2"],
        )
        assert sr.id == "n1"
        assert sr.score == 0.85
        assert len(sr.match_reasons) == 1

    def test_search_result_to_dict(self):
        sr = SearchResult(id="n1", name="X", entity_type="concept", score=1.0)
        d = sr.to_dict()
        assert d["id"] == "n1"
        assert d["score"] == 1.0
        assert d["match_reasons"] == []

    def test_search_result_defaults(self):
        sr = SearchResult()
        assert sr.id == ""
        assert sr.score == 0.0
        assert sr.metadata == {}

    def test_search_query(self):
        q = SearchQuery(text="machine learning", mode="keyword", limit=5)
        assert q.text == "machine learning"
        assert q.mode == "keyword"
        assert q.limit == 5

    def test_search_query_to_dict(self):
        q = SearchQuery(
            text="test", mode="hybrid", entity_types=["concept"],
            min_importance="important", min_confidence=0.5, limit=10,
            include_related=False,
        )
        d = q.to_dict()
        assert d["text"] == "test"
        assert d["mode"] == "hybrid"
        assert d["entity_types"] == ["concept"]
        assert d["min_confidence"] == 0.5
        assert d["include_related"] is False

    def test_search_query_defaults(self):
        q = SearchQuery()
        assert q.mode == "hybrid"
        assert q.limit == 20
        assert q.include_related is True

    def test_search_stats(self):
        stats = SearchStats(
            total_searches=100, avg_results=5.3,
            top_queries=[{"query": "python", "count": 20}],
            search_modes_used={"keyword": 50, "hybrid": 50},
        )
        assert stats.total_searches == 100

    def test_search_stats_to_dict(self):
        stats = SearchStats(total_searches=10, avg_results=3.0)
        d = stats.to_dict()
        assert d["total_searches"] == 10
        assert d["avg_results"] == 3.0

    def test_search_mode_enum(self):
        assert SearchMode.KEYWORD.value == "keyword"
        assert SearchMode.HYBRID.value == "hybrid"
        assert SearchMode.GRAPH.value == "graph"
        assert SearchMode.SEMANTIC.value == "semantic"


# ════════════════════════════════════════════════════════════
# SecondBrainSearch Tests
# ════════════════════════════════════════════════════════════

class TestSecondBrainSearch:
    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.graph = KnowledgeGraph(db_path=self._tmp.name)
        self.search = SecondBrainSearch(self.graph)
        self._seed_graph()

    def _seed_graph(self):
        _run(self.graph.add_node(Node(id="py", label="Python", type="concept",
                                       content="A popular programming language",
                                       metadata='{"importance": "important"}')))
        _run(self.graph.add_node(Node(id="rs", label="Rust", type="concept",
                                       content="Systems programming language",
                                       metadata='{"importance": "useful"}')))
        _run(self.graph.add_node(Node(id="ml", label="Machine Learning", type="concept",
                                       content="Subset of AI using statistical methods",
                                       metadata='{"importance": "permanent"}')))
        _run(self.graph.add_node(Node(id="jarvis", label="JARVIS", type="entity",
                                       content="AI assistant project built with Python",
                                       metadata='{"importance": "permanent"}')))
        _run(self.graph.add_node(Node(id="flask", label="Flask", type="concept",
                                       content="Lightweight Python web framework",
                                       metadata='{"importance": "useful"}')))

        _run(self.graph.add_edge(Edge(source="py", target="ml", relation="used_in", weight=0.9)))
        _run(self.graph.add_edge(Edge(source="py", target="jarvis", relation="built_with", weight=0.95)))
        _run(self.graph.add_edge(Edge(source="flask", target="py", relation="built_with", weight=0.8)))
        _run(self.graph.add_edge(Edge(source="ml", target="py", relation="requires", weight=0.85)))

    def teardown_method(self):
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_keyword_search(self):
        results = _run(self.search.keyword_search("python"))
        assert len(results) >= 2
        names = [r.name for r in results]
        assert "Python" in names

    def test_keyword_search_no_match(self):
        results = _run(self.search.keyword_search("ziglang"))
        assert len(results) == 0

    def test_keyword_search_case_insensitive(self):
        results = _run(self.search.keyword_search("JARVIS"))
        assert len(results) == 1
        assert results[0].name == "JARVIS"

    def test_keyword_search_content_match(self):
        results = _run(self.search.keyword_search("statistical"))
        assert len(results) == 1
        assert results[0].name == "Machine Learning"

    def test_keyword_search_entity_type_filter(self):
        results = _run(self.search.keyword_search("python", entity_types=["entity"]))
        assert all(r.entity_type == "entity" for r in results)

    def test_keyword_search_limit(self):
        results = _run(self.search.keyword_search("python", limit=1))
        assert len(results) == 1

    def test_keyword_search_neighbor_ids(self):
        results = _run(self.search.keyword_search("python"))
        py_result = next(r for r in results if r.name == "Python")
        assert len(py_result.related_entities) > 0

    def test_graph_search(self):
        results = _run(self.search.graph_search("python"))
        assert len(results) >= 2
        assert any(r.name == "Python" for r in results)

    def test_graph_search_traverses_edges(self):
        results = _run(self.search.graph_search("flask", depth=1))
        names = [r.name for r in results]
        assert "Flask" in names
        assert "Python" in names

    def test_graph_search_no_match(self):
        results = _run(self.search.graph_search("nonexistent"))
        assert len(results) == 0

    def test_hybrid_search(self):
        results = _run(self.search.hybrid_search("python"))
        assert len(results) >= 2

    def test_hybrid_search_deduplicates(self):
        results = _run(self.search.hybrid_search("python"))
        ids = [r.id for r in results]
        assert len(ids) == len(set(ids))

    def test_keyword_search_dispatch(self):
        q = SearchQuery(text="python", mode="keyword", limit=10)
        results = _run(self.search.keyword_search(q.text, q.entity_types, q.limit))
        assert len(results) >= 1

    def test_graph_search_dispatch(self):
        q = SearchQuery(text="python", mode="graph", limit=10)
        results = _run(self.search.graph_search(q.text, q.limit))
        assert len(results) >= 1

    def test_hybrid_search_dispatch(self):
        q = SearchQuery(text="python", mode="hybrid", limit=10)
        results = _run(self.search.hybrid_search(q.text, q.limit))
        assert len(results) >= 1

    def test_get_context(self):
        ctx = _run(self.search.get_context("py"))
        assert "entity" in ctx
        assert ctx["entity"]["label"] == "Python"
        assert "neighbors" in ctx

    def test_get_context_not_found(self):
        ctx = _run(self.search.get_context("nonexistent"))
        assert "error" in ctx

    def test_suggest_related(self):
        results = _run(self.search.suggest_related("py"))
        assert len(results) >= 1
        names = [r.name for r in results]
        assert "JARVIS" in names or "Machine Learning" in names or "Flask" in names

    def test_suggest_related_not_found(self):
        results = _run(self.search.suggest_related("nonexistent"))
        assert results == []

    def test_get_stats(self):
        _run(self.search.keyword_search("python"))
        self.search._total_searches = 2
        self.search._total_results = 6
        self.search._query_counts["python"] = 2
        self.search._mode_counts["keyword"] = 2
        stats = _run(self.search.get_stats())
        assert stats.total_searches == 2
        assert stats.avg_results == 3.0
        assert stats.search_modes_used["keyword"] == 2
        assert len(stats.top_queries) == 1

    def test_get_stats_empty(self):
        stats = _run(self.search.get_stats())
        assert stats.total_searches == 0
        assert stats.avg_results == 0.0

    def test_keyword_search_scores_name_match_higher(self):
        results = _run(self.search.keyword_search("python"))
        py_result = next(r for r in results if r.name == "Python")
        other_results = [r for r in results if r.name != "Python"]
        for r in other_results:
            assert py_result.score >= r.score

    def test_apply_filters_entity_types(self):
        all_results = _run(self.search.keyword_search("python"))
        filtered = self.search._apply_filters(all_results, SearchQuery(entity_types=["entity"]))
        assert all(r.entity_type == "entity" for r in filtered)

    def test_apply_filters_no_filter(self):
        all_results = _run(self.search.keyword_search("python"))
        filtered = self.search._apply_filters(all_results, SearchQuery())
        assert len(filtered) == len(all_results)

    def test_suggest_related_sorted_by_weight(self):
        results = _run(self.search.suggest_related("py"))
        if len(results) >= 2:
            assert results[0].score >= results[1].score


class TestSearchRanking:
    def setup_method(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.graph = KnowledgeGraph(db_path=self._tmp.name)
        self.search = SecondBrainSearch(self.graph)
        _run(self.graph.add_node(Node(id="high", label="HighScore", type="concept",
                                       content="Important concept",
                                       metadata='{"importance": "permanent"}')))
        _run(self.graph.add_node(Node(id="low", label="LowScore", type="concept",
                                       content="Temporary idea",
                                       metadata='{"importance": "temporary"}')))
        _run(self.graph.add_edge(Edge(source="high", target="low",
                                       relation="related_to", weight=0.5)))

    def teardown_method(self):
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_rank_results_score_components(self):
        kw = _run(self.search.keyword_search("highscore"))
        query = SearchQuery(text="highscore", mode="keyword")
        ranked = _run(self.search.rank_results(kw, query))
        assert len(ranked) >= 1
        for r in ranked:
            assert r.score > 0

    def test_rank_results_ordering(self):
        results = [
            SearchResult(id="a", name="A", entity_type="concept", score=0.3),
            SearchResult(id="b", name="B", entity_type="concept", score=0.9),
        ]
        query = SearchQuery(text="test")
        ranked = _run(self.search.rank_results(results, query))
        assert ranked[0].score >= ranked[-1].score

    def test_rank_results_with_related_entities(self):
        results = [
            SearchResult(id="high", name="HighScore", entity_type="concept",
                         score=0.8, related_entities=["py"]),
            SearchResult(id="low", name="LowScore", entity_type="concept", score=0.8),
        ]
        query = SearchQuery(text="test")
        ranked = _run(self.search.rank_results(results, query))
        high_r = next(r for r in ranked if r.id == "high")
        low_r = next(r for r in ranked if r.id == "low")
        assert high_r.score > low_r.score

    def test_rank_results_modifies_scores(self):
        results = [
            SearchResult(id="high", name="HighScore", entity_type="concept", score=1.0),
        ]
        query = SearchQuery(text="test")
        ranked = _run(self.search.rank_results(results, query))
        assert ranked[0].score != 1.0

    def test_rank_results_empty(self):
        ranked = _run(self.search.rank_results([], SearchQuery()))
        assert ranked == []
