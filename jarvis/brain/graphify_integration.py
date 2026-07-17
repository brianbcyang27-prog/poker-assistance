"""
Graphify Integration — bridges Graphify knowledge graph output
with JARVIS's existing graph analysis and visualization systems.

Reads graphify-out/graph.json and exposes it through the existing
graph_analysis.py patterns + new query endpoints.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict


class GraphifyIntegration:
    """Loads and queries the Graphify knowledge graph."""

    def __init__(self, graph_dir: str = None):
        if graph_dir is None:
            # Navigate from jarvis/brain/ to project root
            graph_dir = str(Path(__file__).parent.parent.parent / "graphify-out")
        self.graph_dir = Path(graph_dir)
        self.graph_path = self.graph_dir / "graph.json"
        self._graph = None
        self._nodes_by_id = {}
        self._adjacency = defaultdict(list)
        self._communities = defaultdict(list)
        self._loaded = False

    def load(self) -> bool:
        """Load graph.json into memory."""
        if not self.graph_path.exists():
            return False

        try:
            with open(self.graph_path, "r") as f:
                self._graph = json.load(f)

            # Index nodes by ID
            for node in self._graph.get("nodes", []):
                nid = node.get("id", "")
                self._nodes_by_id[nid] = node
                comm = node.get("community", -1)
                self._communities[comm].append(nid)

            # Build adjacency list
            for link in self._graph.get("links", []):
                src = link.get("source", "")
                tgt = link.get("target", "")
                self._adjacency[src].append({
                    "target": tgt,
                    "relation": link.get("relation", "unknown"),
                    "confidence": link.get("confidence", "UNKNOWN"),
                    "confidence_score": link.get("confidence_score", 0.0),
                    "weight": link.get("weight", 1.0),
                    "source_file": link.get("source_file", ""),
                })
                self._adjacency[tgt].append({
                    "target": src,
                    "relation": link.get("relation", "unknown"),
                    "confidence": link.get("confidence", "UNKNOWN"),
                    "confidence_score": link.get("confidence_score", 0.0),
                    "weight": link.get("weight", 1.0),
                    "source_file": link.get("source_file", ""),
                })

            self._loaded = True
            return True
        except Exception:
            return False

    @property
    def is_loaded(self):
        return self._loaded

    @property
    def node_count(self):
        return len(self._nodes_by_id)

    @property
    def edge_count(self):
        return len(self._graph.get("links", [])) if self._graph else 0

    @property
    def community_count(self):
        return len(self._communities)

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics."""
        if not self._loaded:
            return {"loaded": False}

        node_types = defaultdict(int)
        for node in self._nodes_by_id.values():
            node_types[node.get("file_type", "unknown")] += 1

        relation_types = defaultdict(int)
        for link in self._graph.get("links", []):
            relation_types[link.get("relation", "unknown")] += 1

        return {
            "loaded": True,
            "nodes": self.node_count,
            "edges": self.edge_count,
            "communities": self.community_count,
            "node_types": dict(node_types),
            "relation_types": dict(relation_types),
            "top_hubs": self._get_top_hubs(10),
        }

    def _get_top_hubs(self, n: int = 10) -> List[Dict]:
        """Get the N most connected nodes."""
        degrees = defaultdict(int)
        for nid, neighbors in self._adjacency.items():
            degrees[nid] = len(neighbors)

        top = sorted(degrees.items(), key=lambda x: -x[1])[:n]
        return [
            {
                "id": nid,
                "label": self._nodes_by_id.get(nid, {}).get("label", nid),
                "degree": deg,
                "community": self._nodes_by_id.get(nid, {}).get("community", -1),
                "file_type": self._nodes_by_id.get(nid, {}).get("file_type", "unknown"),
            }
            for nid, deg in top
        ]

    def query(self, question: str) -> Dict[str, Any]:
        """Simple keyword-based graph query."""
        if not self._loaded:
            return {"error": "Graph not loaded"}

        question_lower = question.lower()
        matches = []

        # Search nodes by label
        for nid, node in self._nodes_by_id.items():
            label = node.get("label", "").lower()
            if any(word in label for word in question_lower.split() if len(word) > 2):
                neighbors = self._adjacency.get(nid, [])
                matches.append({
                    "node": node,
                    "degree": len(neighbors),
                    "neighbors": [
                        {
                            "label": self._nodes_by_id.get(n["target"], {}).get("label", n["target"]),
                            "relation": n["relation"],
                            "confidence": n["confidence"],
                        }
                        for n in neighbors[:10]
                    ],
                })

        # Sort by relevance (degree * match count)
        matches.sort(key=lambda x: x["degree"], reverse=True)

        return {
            "question": question,
            "matches": len(matches),
            "results": matches[:20],
        }

    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get a node and its connections."""
        if not self._loaded:
            return None

        node = self._nodes_by_id.get(node_id)
        if not node:
            # Try fuzzy match
            for nid, n in self._nodes_by_id.items():
                if node_id.lower() in n.get("label", "").lower():
                    node = n
                    node_id = nid
                    break

        if not node:
            return None

        neighbors = self._adjacency.get(node_id, [])
        return {
            "node": node,
            "connections": len(neighbors),
            "neighbors": [
                {
                    "id": n["target"],
                    "label": self._nodes_by_id.get(n["target"], {}).get("label", n["target"]),
                    "relation": n["relation"],
                    "confidence": n["confidence"],
                    "source_file": n["source_file"],
                }
                for n in neighbors
            ],
        }

    def shortest_path(self, source: str, target: str, max_depth: int = 6) -> Optional[List[Dict]]:
        """Find shortest path between two nodes using BFS."""
        if not self._loaded:
            return None

        # Find source and target IDs
        src_id = self._find_node_id(source)
        tgt_id = self._find_node_id(target)

        if not src_id or not tgt_id:
            return None

        # BFS
        from collections import deque
        queue = deque([(src_id, [src_id])])
        visited = {src_id}

        while queue:
            current, path = queue.popleft()
            if len(path) > max_depth:
                continue

            if current == tgt_id:
                return [
                    {
                        "id": nid,
                        "label": self._nodes_by_id.get(nid, {}).get("label", nid),
                        "community": self._nodes_by_id.get(nid, {}).get("community", -1),
                    }
                    for nid in path
                ]

            for neighbor in self._adjacency.get(current, []):
                nxt = neighbor["target"]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, path + [nxt]))

        return None

    def _find_node_id(self, name: str) -> Optional[str]:
        """Find node ID by label (exact or fuzzy match)."""
        name_lower = name.lower()

        # Exact match
        for nid, node in self._nodes_by_id.items():
            if node.get("label", "").lower() == name_lower:
                return nid

        # Partial match
        for nid, node in self._nodes_by_id.items():
            if name_lower in node.get("label", "").lower():
                return nid

        return None

    def get_community(self, community_id: int) -> List[Dict]:
        """Get all nodes in a community."""
        if not self._loaded:
            return []

        node_ids = self._communities.get(community_id, [])
        return [
            self._nodes_by_id.get(nid, {})
            for nid in node_ids
        ]

    def to_three_js(self, max_nodes: int = 500) -> Dict:
        """Export graph in a format suitable for Three.js visualization."""
        if not self._loaded:
            return {"nodes": [], "edges": []}

        # Get top nodes by degree
        degrees = defaultdict(int)
        for link in self._graph.get("links", []):
            degrees[link["source"]] += 1
            degrees[link["target"]] += 1

        top_nodes = sorted(degrees.items(), key=lambda x: -x[1])[:max_nodes]
        node_ids = {nid for nid, _ in top_nodes}

        # Color by community
        nodes = []
        for nid, deg in top_nodes:
            node = self._nodes_by_id.get(nid, {})
            nodes.append({
                "id": nid,
                "label": node.get("label", nid),
                "community": node.get("community", 0),
                "degree": deg,
                "file_type": node.get("file_type", "unknown"),
            })

        edges = []
        for link in self._graph.get("links", []):
            if link["source"] in node_ids and link["target"] in node_ids:
                edges.append({
                    "source": link["source"],
                    "target": link["target"],
                    "relation": link.get("relation", "unknown"),
                })

        return {"nodes": nodes, "edges": edges}


# Singleton
_graphify: Optional[GraphifyIntegration] = None


def get_graphify() -> GraphifyIntegration:
    global _graphify
    if _graphify is None:
        _graphify = GraphifyIntegration()
        _graphify.load()
    return _graphify
