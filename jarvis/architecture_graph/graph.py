"""Main ArchGraph class for building and analyzing architecture graphs."""

import os
from collections import deque
from typing import Any, Dict, List, Optional, Set

from .analyzer import (
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
from .models import GraphEdge, GraphMetrics, GraphNode


class ArchGraph:
    """Live architecture graph engine for repository visualization."""

    def __init__(self) -> None:
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self._adj: Dict[str, List[str]] = {}
        self._adj_rev: Dict[str, List[str]] = {}

    async def build(self, repo_path: str) -> None:
        """Build full graph from a repository path."""
        repo_path = os.path.abspath(repo_path)
        if not os.path.isdir(repo_path):
            raise ValueError(f"Not a directory: {repo_path}")

        # Walk the filesystem
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden dirs and common non-source dirs
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in ("__pycache__", "node_modules", ".git", "venv", ".venv", "dist", "build")
            ]

            rel_root = os.path.relpath(root, repo_path)

            # Add directory as module node
            if rel_root != ".":
                node_id = rel_root.replace(os.sep, "/")
                if node_id not in self.nodes:
                    self.nodes[node_id] = GraphNode(
                        id=node_id,
                        label=os.path.basename(root),
                        type="module",
                        layer="infrastructure",
                    )

            # Process Python files
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                if fname.startswith("."):
                    continue

                filepath = os.path.join(root, fname)
                rel_path = os.path.relpath(filepath, repo_path).replace(os.sep, "/")
                module_id = rel_path[:-3]  # Remove .py

                # Parse the file
                imports, definitions, line_count = parse_file_ast(filepath)

                # Create file node
                self.nodes[module_id] = GraphNode(
                    id=module_id,
                    label=fname[:-3],
                    type="module",
                    layer="infrastructure",
                    size=line_count,
                )

                # Add edge from parent directory
                parent = os.path.dirname(module_id)
                if parent and parent != module_id:
                    if parent not in self.nodes:
                        self.nodes[parent] = GraphNode(
                            id=parent,
                            label=os.path.basename(parent),
                            type="module",
                            layer="infrastructure",
                        )
                    self._add_edge_internal(
                        GraphEdge(source=parent, target=module_id, type="depends")
                    )

                # Create class/function nodes
                for defn in definitions:
                    child_id = f"{module_id}::{defn}"
                    child_type = "class" if defn[0].isupper() else "function"
                    self.nodes[child_id] = GraphNode(
                        id=child_id,
                        label=defn,
                        type=child_type,
                        layer="business",
                    )
                    self._add_edge_internal(
                        GraphEdge(source=module_id, target=child_id, type="depends")
                    )

                # Create edges for imports
                for imp in imports:
                    target_id = imp.replace(".", "/")
                    # Try to find matching node
                    if target_id in self.nodes:
                        self._add_edge_internal(
                            GraphEdge(source=module_id, target=target_id, type="imports")
                        )
                    else:
                        # Create placeholder for external dependency
                        ext_id = imp.split(".")[0]
                        if ext_id not in self.nodes:
                            self.nodes[ext_id] = GraphNode(
                                id=ext_id,
                                label=ext_id,
                                type="module",
                                layer="infrastructure",
                                metadata={"external": True},
                            )
                        self._add_edge_internal(
                            GraphEdge(source=module_id, target=ext_id, type="imports")
                        )

        # Detect layers and clusters after build
        detect_layers(self.nodes, self.edges)

    def _add_edge_internal(self, edge: GraphEdge) -> None:
        """Add an edge internally, avoiding duplicates."""
        key = f"{edge.source}->{edge.target}:{edge.type}"
        if key not in self.edges:
            self.edges[key] = edge
            if edge.source not in self._adj:
                self._adj[edge.source] = []
            self._adj[edge.source].append(edge.target)
            if edge.target not in self._adj_rev:
                self._adj_rev[edge.target] = []
            self._adj_rev[edge.target].append(edge.source)
            if edge.bidirectional:
                if edge.target not in self._adj:
                    self._adj[edge.target] = []
                self._adj[edge.target].append(edge.source)
                if edge.source not in self._adj_rev:
                    self._adj_rev[edge.source] = []
                self._adj_rev[edge.source].append(edge.target)

    async def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    async def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self._add_edge_internal(edge)

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    async def get_neighbors(self, node_id: str, direction: str = "both") -> List[GraphNode]:
        """Get neighbors of a node.

        direction: 'in', 'out', or 'both'
        """
        neighbor_ids: Set[str] = set()

        if direction in ("out", "both"):
            for nid in self._adj.get(node_id, []):
                neighbor_ids.add(nid)

        if direction in ("in", "both"):
            for nid in self._adj_rev.get(node_id, []):
                neighbor_ids.add(nid)

        return [self.nodes[nid] for nid in neighbor_ids if nid in self.nodes]

    async def get_shortest_path(self, source: str, target: str) -> List[str]:
        """Find shortest path between two nodes using BFS."""
        if source == target:
            return [source]

        if source not in self.nodes or target not in self.nodes:
            return []

        visited: Set[str] = {source}
        queue: deque = deque([(source, [source])])

        while queue:
            current, path = queue.popleft()
            for neighbor in self._adj.get(current, []):
                if neighbor == target:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []  # No path found

    async def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies."""
        return detect_cycles(self.nodes, self.edges)

    async def detect_layers(self) -> Dict[str, List[str]]:
        """Detect architecture layers."""
        return detect_layers(self.nodes, self.edges)

    async def detect_clusters(self) -> Dict[str, List[str]]:
        """Detect modules/clusters using connected components."""
        clusters = detect_clusters(self.nodes, self.edges)
        return {f"cluster_{i}": c for i, c in enumerate(clusters)}

    async def compute_metrics(self) -> GraphMetrics:
        """Compute all graph metrics."""
        n = len(self.nodes)
        e = len(self.edges)

        # Density: actual edges / possible edges
        density = e / (n * (n - 1)) if n > 1 else 0.0

        # Degree stats
        degrees = []
        for nid in self.nodes:
            out_deg = len(self._adj.get(nid, []))
            in_deg = len(self._adj_rev.get(nid, []))
            degrees.append(out_deg + in_deg)

        avg_degree = sum(degrees) / n if n > 0 else 0.0
        max_degree = max(degrees) if degrees else 0

        # Centrality
        centrality = compute_centrality(self.nodes, self.edges)

        # Clusters
        clusters = detect_clusters(self.nodes, self.edges)

        # Layers
        layers = detect_layers(self.nodes, self.edges)

        # Critical path
        critical_path = find_critical_path(self.nodes, self.edges)

        # Cycles (count as proxy for cyclomatic complexity)
        cycles = detect_cycles(self.nodes, self.edges)
        cyclomatic_complexity = len(cycles) + 1  # Base is 1

        # Coupling and cohesion
        coupling = compute_coupling(self.nodes, self.edges)
        cohesion = compute_cohesion(self.nodes, self.edges)

        return GraphMetrics(
            node_count=n,
            edge_count=e,
            density=density,
            avg_degree=avg_degree,
            max_degree=max_degree,
            centrality=centrality,
            clusters=clusters,
            layers=layers,
            critical_path=critical_path,
            cyclomatic_complexity=cyclomatic_complexity,
            coupling_score=coupling,
            cohesion_score=cohesion,
        )

    async def to_dict(self) -> Dict[str, Any]:
        """Serialize the graph for visualization."""
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges.values()],
        }

    async def to_mermaid(self) -> str:
        """Generate Mermaid diagram syntax."""
        layers = detect_layers(self.nodes, self.edges)
        return generate_mermaid(self.nodes, self.edges, layers)

    async def get_critical_path(self) -> List[str]:
        """Get the most depended-upon chain."""
        return find_critical_path(self.nodes, self.edges)
