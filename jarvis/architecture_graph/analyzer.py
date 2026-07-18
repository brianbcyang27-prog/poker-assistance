"""Graph analysis utilities for the Architecture Graph engine."""

import ast
import os
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .models import GraphEdge, GraphMetrics, GraphNode


def detect_layers(nodes: Dict[str, GraphNode], edges: Dict[str, GraphEdge]) -> Dict[str, List[str]]:
    """Detect architecture layers from import patterns.

    Layers: presentation -> business -> data -> infrastructure
    Nodes with more outgoing imports are higher-level (presentation).
    Nodes with more incoming imports are lower-level (infrastructure).
    """
    layers: Dict[str, List[str]] = {
        "presentation": [],
        "business": [],
        "data": [],
        "infrastructure": [],
    }

    # Compute import depth for each node
    in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
    out_degree: Dict[str, int] = {nid: 0 for nid in nodes}

    for edge in edges.values():
        if edge.source in in_degree:
            out_degree[edge.source] = out_degree.get(edge.source, 0) + 1
        if edge.target in in_degree:
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    for nid, node in nodes.items():
        od = out_degree.get(nid, 0)
        ind = in_degree.get(nid, 0)

        # Heuristic: high out-degree = presentation, high in-degree = infrastructure
        if od > ind + 2:
            layer = "presentation"
        elif od > 0 and ind > 0:
            layer = "business"
        elif ind > od:
            layer = "data"
        else:
            layer = "infrastructure"

        node.layer = layer
        layers[layer].append(nid)

    return layers


def detect_clusters(nodes: Dict[str, GraphNode], edges: Dict[str, GraphEdge]) -> List[List[str]]:
    """Detect clusters using connected components (BFS)."""
    visited: Set[str] = set()
    clusters: List[List[str]] = []

    # Build adjacency list (undirected)
    adj: Dict[str, List[str]] = {nid: [] for nid in nodes}
    for edge in edges.values():
        if edge.source in adj and edge.target in adj:
            adj[edge.source].append(edge.target)
            adj[edge.target].append(edge.source)

    for nid in nodes:
        if nid in visited:
            continue
        cluster: List[str] = []
        queue = deque([nid])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            cluster.append(current)
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        if cluster:
            clusters.append(cluster)

    return clusters


def compute_centrality(nodes: Dict[str, GraphNode], edges: Dict[str, GraphEdge]) -> Dict[str, float]:
    """Compute degree centrality (incoming edges / total nodes)."""
    n = len(nodes)
    if n <= 1:
        return {nid: 0.0 for nid in nodes}

    in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
    for edge in edges.values():
        if edge.target in in_degree:
            in_degree[edge.target] += 1

    max_possible = n - 1
    return {nid: count / max_possible for nid, count in in_degree.items()}


def find_critical_path(nodes: Dict[str, GraphNode], edges: Dict[str, GraphEdge]) -> List[str]:
    """Find the most depended-upon chain (critical path).

    Uses longest path in the DAG of dependencies.
    Falls back to most central nodes if cycles exist.
    """
    in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
    adj: Dict[str, List[str]] = {nid: [] for nid in nodes}

    for edge in edges.values():
        if edge.source in adj and edge.target in in_degree:
            adj[edge.source].append(edge.target)
            in_degree[edge.target] += 1

    # Topological sort (Kahn's algorithm)
    queue = deque([nid for nid, d in in_degree.items() if d == 0])
    topo_order: List[str] = []
    temp_in = dict(in_degree)

    while queue:
        node = queue.popleft()
        topo_order.append(node)
        for neighbor in adj.get(node, []):
            temp_in[neighbor] -= 1
            if temp_in[neighbor] == 0:
                queue.append(neighbor)

    if len(topo_order) != len(nodes):
        # Cycle exists — fall back to most central nodes
        centrality = compute_centrality(nodes, edges)
        sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        return [nid for nid, _ in sorted_nodes[:10]]

    # Longest path in DAG
    dist: Dict[str, int] = {nid: 0 for nid in nodes}
    pred: Dict[str, Optional[str]] = {nid: None for nid in nodes}

    for node in topo_order:
        for neighbor in adj.get(node, []):
            if dist[neighbor] < dist[node] + 1:
                dist[neighbor] = dist[node] + 1
                pred[neighbor] = node

    # Find the end of the longest path
    end_node = max(dist, key=lambda x: dist[x])
    path: List[str] = []
    current: Optional[str] = end_node
    while current is not None:
        path.append(current)
        current = pred[current]
    path.reverse()

    return path


def detect_cycles(nodes: Dict[str, GraphNode], edges: Dict[str, GraphEdge]) -> List[List[str]]:
    """Detect circular dependencies using DFS."""
    adj: Dict[str, List[str]] = {nid: [] for nid in nodes}
    for edge in edges.values():
        if edge.source in adj and edge.target in adj:
            adj[edge.source].append(edge.target)

    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path_stack: List[str] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.add(node)
        path_stack.append(node)

        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path_stack.index(neighbor)
                cycle = path_stack[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path_stack.pop()
        rec_stack.discard(node)

    for nid in nodes:
        if nid not in visited:
            dfs(nid)

    return cycles


def compute_coupling(nodes: Dict[str, GraphNode], edges: Dict[str, GraphEdge]) -> float:
    """Compute coupling score (ratio of cross-module edges to total possible)."""
    n = len(nodes)
    if n <= 1:
        return 0.0

    # Group nodes by their module prefix (first two path components)
    modules: Dict[str, Set[str]] = {}
    for nid in nodes:
        parts = nid.split("/")
        module = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
        if module not in modules:
            modules[module] = set()
        modules[module].add(nid)

    m = len(modules)
    if m <= 1:
        return 0.0

    # Count cross-module edges
    cross_edges = 0
    for edge in edges.values():
        src_parts = edge.source.split("/")
        tgt_parts = edge.target.split("/")
        src_mod = "/".join(src_parts[:2]) if len(src_parts) >= 2 else src_parts[0]
        tgt_mod = "/".join(tgt_parts[:2]) if len(tgt_parts) >= 2 else tgt_parts[0]
        if src_mod != tgt_mod:
            cross_edges += 1

    # Normalize: cross_edges / possible cross-module edges
    possible = n * (n - 1)
    return min(cross_edges / possible, 1.0) if possible > 0 else 0.0


def compute_cohesion(nodes: Dict[str, GraphNode], edges: Dict[str, GraphEdge]) -> float:
    """Compute cohesion score (ratio of internal edges to total possible within clusters)."""
    n = len(nodes)
    if n <= 1:
        return 1.0

    # Group by layer
    layer_nodes: Dict[str, List[str]] = {}
    for nid, node in nodes.items():
        if node.layer not in layer_nodes:
            layer_nodes[node.layer] = []
        layer_nodes[node.layer].append(nid)

    total_internal = 0
    total_possible = 0

    for layer, lnodes in layer_nodes.items():
        ln = len(lnodes)
        total_possible += ln * (ln - 1) // 2

        # Count edges within this layer
        node_set = set(lnodes)
        for edge in edges.values():
            if edge.source in node_set and edge.target in node_set:
                total_internal += 1

    return total_internal / total_possible if total_possible > 0 else 1.0


def generate_mermaid(
    nodes: Dict[str, GraphNode],
    edges: Dict[str, GraphEdge],
    layers: Optional[Dict[str, List[str]]] = None,
) -> str:
    """Generate Mermaid diagram syntax in graph TD format."""
    lines = ["graph TD"]

    if layers is None:
        layer_nodes: Dict[str, List[str]] = {}
        for nid, node in nodes.items():
            if node.layer not in layer_nodes:
                layer_nodes[node.layer] = []
            layer_nodes[node.layer].append(nid)
    else:
        layer_nodes = layers

    # Create subgraphs for layers
    for layer_name, layer_nids in layer_nodes.items():
        if not layer_nids:
            continue
        lines.append(f"    subgraph {layer_name}")
        for nid in layer_nids:
            node = nodes[nid]
            safe_id = nid.replace("/", "_").replace(".", "_").replace("-", "_")
            label = node.label.replace('"', "'")
            lines.append(f'        {safe_id}["{label}"]')
        lines.append("    end")

    # Add edges
    edge_labels = {
        "imports": "imports",
        "calls": "calls",
        "depends": "depends",
        "extends": "extends",
        "implements": "implements",
        "uses": "uses",
        "api": "API",
        "database": "DB",
        "event": "event",
    }

    for edge in edges.values():
        src = edge.source.replace("/", "_").replace(".", "_").replace("-", "_")
        tgt = edge.target.replace("/", "_").replace(".", "_").replace("-", "_")
        label = edge_labels.get(edge.type, edge.type)
        if edge.bidirectional:
            lines.append(f"    {src} <-->|{label}| {tgt}")
        else:
            lines.append(f"    {src} -->|{label}| {tgt}")

    return "\n".join(lines)


def parse_file_ast(filepath: str) -> Tuple[List[str], List[str], int]:
    """Parse a Python file with AST to extract imports, definitions, and line count.

    Returns (imports, definitions, line_count).
    """
    imports: List[str] = []
    definitions: List[str] = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        line_count = content.count("\n") + 1

        tree = ast.parse(content, filename=filepath)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                definitions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                definitions.append(node.name)

        return imports, definitions, line_count

    except (SyntaxError, UnicodeDecodeError, ValueError):
        return [], [], 0
