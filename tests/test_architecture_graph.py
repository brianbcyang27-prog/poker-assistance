"""Tests for JARVIS Architecture Graph engine (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.architecture_graph import (
    ArchGraph,
    GraphNode,
    GraphEdge,
    GraphMetrics,
    SubGraph,
    compute_centrality,
    compute_cohesion,
    compute_coupling,
    detect_clusters,
    detect_cycles,
    detect_layers,
    find_critical_path,
    generate_mermaid,
    parse_file_ast,
)

REPO_PATH = os.path.join(os.path.dirname(__file__), "..")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestGraphNodeModel:
    def test_create_node(self):
        node = GraphNode(id="a", label="Alpha", type="module")
        assert node.id == "a"
        assert node.label == "Alpha"
        assert node.layer == "infrastructure"

    def test_node_to_dict(self):
        node = GraphNode(id="b", label="Beta", type="class", size=100)
        d = node.to_dict()
        assert d["id"] == "b"
        assert d["size"] == 100
        assert d["health_score"] == 1.0


class TestGraphEdgeModel:
    def test_create_edge(self):
        edge = GraphEdge(source="a", target="b", type="imports")
        assert edge.source == "a"
        assert edge.target == "b"
        assert edge.weight == 1.0

    def test_edge_to_dict(self):
        edge = GraphEdge(source="x", target="y", type="calls", bidirectional=True)
        d = edge.to_dict()
        assert d["bidirectional"] is True


class TestGraphMetrics:
    def test_create_metrics(self):
        m = GraphMetrics(node_count=10, edge_count=15, density=0.33)
        assert m.node_count == 10
        assert m.critical_path == []

    def test_metrics_to_dict(self):
        m = GraphMetrics(node_count=5)
        d = m.to_dict()
        assert d["node_count"] == 5


class TestSubGraph:
    def test_create_subgraph(self):
        sg = SubGraph(nodes=["a", "b"], label="Cluster 1")
        assert len(sg.nodes) == 2
        assert sg.label == "Cluster 1"


# ════════════════════════════════════════════════════════════
# Analyzer Function Tests
# ════════════════════════════════════════════════════════════

class TestAnalyzerFunctions:
    def test_parse_file_ast(self):
        sample = os.path.join(REPO_PATH, "jarvis", "cli.py")
        if os.path.isfile(sample):
            imports, definitions, line_count = parse_file_ast(sample)
            assert isinstance(imports, list)
            assert isinstance(definitions, list)
            assert line_count > 0

    def test_detect_layers_empty(self):
        layers = detect_layers({}, {})
        assert "presentation" in layers
        assert "infrastructure" in layers

    def test_detect_cycles_empty(self):
        cycles = detect_cycles({}, {})
        assert cycles == []

    def test_detect_clusters_empty(self):
        clusters = detect_clusters({}, {})
        assert clusters == []

    def test_compute_centrality_empty(self):
        c = compute_centrality({}, {})
        assert c == {}

    def test_compute_coupling_single_node(self):
        nodes = {"a": GraphNode(id="a", label="A", type="module")}
        edges = {}
        coupling = compute_coupling(nodes, edges)
        assert coupling == 0.0

    def test_compute_cohesion_single_node(self):
        nodes = {"a": GraphNode(id="a", label="A", type="module")}
        cohesion = compute_cohesion(nodes, {})
        assert cohesion == 1.0

    def test_generate_mermaid_empty(self):
        result = generate_mermaid({}, {})
        assert result == "graph TD"

    def test_find_critical_path_single_node(self):
        nodes = {"a": GraphNode(id="a", label="A", type="module")}
        path = find_critical_path(nodes, {})
        assert path == ["a"]


# ════════════════════════════════════════════════════════════
# ArchGraph Integration Tests
# ════════════════════════════════════════════════════════════

class TestArchGraph:
    def setup_method(self):
        self.graph = ArchGraph()
        _run(self.graph.build(REPO_PATH))

    def test_nodes_populated(self):
        assert len(self.graph.nodes) > 0

    def test_edges_populated(self):
        assert len(self.graph.edges) > 0

    def test_get_node(self):
        node = _run(self.graph.get_node("jarvis"))
        assert node is not None
        assert node.type == "module"

    def test_detect_layers(self):
        layers = _run(self.graph.detect_layers())
        assert isinstance(layers, dict)
        assert "infrastructure" in layers
        assert "business" in layers

    def test_detect_clusters(self):
        clusters = _run(self.graph.detect_clusters())
        assert isinstance(clusters, dict)
        assert len(clusters) > 0

    def test_compute_metrics(self):
        metrics = _run(self.graph.compute_metrics())
        assert isinstance(metrics, GraphMetrics)
        assert metrics.node_count > 0
        assert metrics.edge_count > 0
        assert metrics.density >= 0
        assert isinstance(metrics.centrality, dict)

    def test_detect_cycles(self):
        cycles = _run(self.graph.detect_cycles())
        assert isinstance(cycles, list)

    def test_get_critical_path(self):
        path = _run(self.graph.get_critical_path())
        assert isinstance(path, list)
        assert len(path) > 0

    def test_to_dict(self):
        d = _run(self.graph.to_dict())
        assert "nodes" in d
        assert "edges" in d
        assert len(d["nodes"]) > 0

    def test_to_mermaid(self):
        mermaid = _run(self.graph.to_mermaid())
        assert isinstance(mermaid, str)
        assert "graph TD" in mermaid

    def test_get_neighbors(self):
        # Pick a node that likely has neighbors
        for nid in self.graph.nodes:
            neighbors = _run(self.graph.get_neighbors(nid))
            assert isinstance(neighbors, list)
            break

    def test_get_shortest_path(self):
        node_ids = list(self.graph.nodes.keys())
        if len(node_ids) >= 2:
            path = _run(self.graph.get_shortest_path(node_ids[0], node_ids[1]))
            assert isinstance(path, list)
