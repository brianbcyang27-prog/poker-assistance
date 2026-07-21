"""Knowledge Graph v2 — Enhanced graph with auto-extraction, traversal, and importance.

Extends the existing graph.py with:
- Auto entity/relation extraction from text
- Shortest path between nodes
- Community detection (connected components)
- PageRank-like importance scoring
- Graph statistics and health
"""

import re
import time
import math
from collections import defaultdict, deque
from typing import Optional
from loguru import logger


class GraphAnalyzer:
    """Graph algorithms on top of the existing KnowledgeGraph."""

    def __init__(self, graph):
        self._graph = graph

    async def shortest_path(self, source_id: str, target_id: str, max_depth: int = 6) -> Optional[list[str]]:
        """BFS shortest path between two nodes."""
        conn = await self._graph._get_conn()

        visited = {source_id}
        queue = deque([(source_id, [source_id])])

        while queue:
            current, path = queue.popleft()
            if current == target_id:
                return path
            if len(path) > max_depth:
                continue

            # Get neighbors (both directions)
            cursor = await conn.execute(
                "SELECT target FROM edges WHERE source = ? UNION "
                "SELECT source FROM edges WHERE target = ?",
                (current, current),
            )
            rows = await cursor.fetchall()

            for row in rows:
                neighbor = row[0]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None  # No path found

    async def connected_components(self) -> list[list[str]]:
        """Find connected components (communities)."""
        conn = await self._graph._get_conn()
        cursor = await conn.execute("SELECT id FROM nodes")
        nodes = await cursor.fetchall()
        node_ids = {r[0] for r in nodes}

        visited = set()
        components = []

        for node_id in node_ids:
            if node_id in visited:
                continue
            # BFS from this node
            component = []
            queue = deque([node_id])
            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)
                component.append(current)

                cursor = await conn.execute(
                    "SELECT target FROM edges WHERE source = ? UNION "
                    "SELECT source FROM edges WHERE target = ?",
                    (current, current),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    if row[0] not in visited:
                        queue.append(row[0])

            components.append(component)

        return components

    async def pagerank(self, damping: float = 0.85, iterations: int = 20) -> dict[str, float]:
        """Compute PageRank importance scores for all nodes."""
        conn = await self._graph._get_conn()
        cursor = await conn.execute("SELECT id FROM nodes")
        nodes = await cursor.fetchall()
        node_ids = [r[0] for r in nodes]
        n = len(node_ids)
        if n == 0:
            return {}

        # Initialize scores
        scores = {nid: 1.0 / n for nid in node_ids}
        out_degree = {}

        # Get out-degrees
        for nid in node_ids:
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM edges WHERE source = ?", (nid,)
            )
            row = await cursor.fetchone()
            out_degree[nid] = max(1, row[0])

        # Iterate
        for _ in range(iterations):
            new_scores = {}
            for nid in node_ids:
                # Sum contributions from incoming edges
                cursor = await conn.execute(
                    "SELECT source FROM edges WHERE target = ?", (nid,)
                )
                incoming = await cursor.fetchall()
                rank_sum = 0.0
                for row in incoming:
                    src = row[0]
                    if src in scores:
                        rank_sum += scores[src] / out_degree.get(src, 1)
                new_scores[nid] = (1 - damping) / n + damping * rank_sum
            scores = new_scores

        return scores

    async def get_ego_graph(self, node_id: str, radius: int = 2) -> dict:
        """Get the ego graph (neighborhood) of a node up to given radius."""
        conn = await self._graph._get_conn()
        visited = {node_id: 0}
        queue = deque([(node_id, 0)])
        nodes = []
        edges = []

        while queue:
            current, depth = queue.popleft()
            if depth >= radius:
                continue

            # Get node info
            cursor = await conn.execute("SELECT * FROM nodes WHERE id = ?", (current,))
            row = await cursor.fetchone()
            if row:
                nodes.append(dict(row))

            # Get edges
            cursor = await conn.execute(
                "SELECT e.*, s.label as source_label, t.label as target_label "
                "FROM edges e "
                "JOIN nodes s ON e.source = s.id "
                "JOIN nodes t ON e.target = t.id "
                "WHERE e.source = ? OR e.target = ?",
                (current, current),
            )
            rows = await cursor.fetchall()
            for r in rows:
                rd = dict(r)
                edge_key = (rd["source"], rd["target"], rd["relation"])
                edges.append(rd)
                # Add unseen neighbors
                neighbor = rd["target"] if rd["source"] == current else rd["source"]
                if neighbor not in visited:
                    visited[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))

        return {"nodes": nodes, "edges": edges}

    async def get_stats(self) -> dict:
        """Comprehensive graph statistics."""
        conn = await self._graph._get_conn()
        cursor = await conn.execute("SELECT COUNT(*) FROM nodes")
        node_count = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM edges")
        edge_count = (await cursor.fetchone())[0]

        # Type distribution
        cursor = await conn.execute(
            "SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type"
        )
        types = await cursor.fetchall()
        type_dist = {r["type"]: r["cnt"] for r in types}

        # Relation distribution
        cursor = await conn.execute(
            "SELECT relation, COUNT(*) as cnt FROM edges GROUP BY relation"
        )
        rels = await cursor.fetchall()
        rel_dist = {r["relation"]: r["cnt"] for r in rels}

        # Density
        max_edges = node_count * (node_count - 1) if node_count > 1 else 1
        density = edge_count / max_edges if max_edges > 0 else 0

        # Average degree
        avg_degree = (2 * edge_count / node_count) if node_count > 0 else 0

        # Connected components
        components = await self.connected_components()
        num_components = len(components)
        largest_cc = max(len(c) for c in components) if components else 0

        return {
            "nodes": node_count,
            "edges": edge_count,
            "density": round(density, 4),
            "avg_degree": round(avg_degree, 2),
            "type_distribution": type_dist,
            "relation_distribution": rel_dist,
            "connected_components": num_components,
            "largest_component_size": largest_cc,
        }


class EntityExtractor:
    """Extract entities and relations from text using pattern matching."""

    # Common entity patterns
    ENTITY_PATTERNS = {
        "person": r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
        "file": r'[\w/\\.-]+\.\w{1,5}\b',
        "url": r'https?://[^\s<>"]+',
        "command": r'(?:npm|pip|python|git|curl|mkdir|cd|ls|cat|grep)\s+\S+',
        "number": r'\b\d+(?:\.\d+)?\b',
    }

    # Relation patterns
    RELATION_PATTERNS = [
        (r'(.+?)\s+(?:uses?|uses?|depends on|requires)\s+(.+)', "depends_on"),
        (r'(.+?)\s+(?:is part of|belongs to|in)\s+(.+)', "part_of"),
        (r'(.+?)\s+(?:creates?|generates?|produces?)\s+(.+)', "creates"),
        (r'(.+?)\s+(?:calls?|invokes?|triggers?)\s+(.+)', "calls"),
        (r'(.+?)\s+(?:related to|similar to|like)\s+(.+)', "related_to"),
    ]

    def extract_entities(self, text: str) -> list[dict]:
        """Extract entities from text."""
        entities = []
        for etype, pattern in self.ENTITY_PATTERNS.items():
            matches = re.findall(pattern, text)
            for match in set(matches):
                entities.append({
                    "type": etype,
                    "value": match,
                    "id": f"{etype}_{re.sub(r'[^a-zA-Z0-9]', '_', match).lower()[:50]}",
                })
        return entities

    def extract_relations(self, text: str) -> list[dict]:
        """Extract relations from text."""
        relations = []
        for pattern, rel_type in self.RELATION_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for source, target in matches:
                source = source.strip()[:100]
                target = target.strip()[:100]
                if source and target and source != target:
                    relations.append({
                        "source": source,
                        "target": target,
                        "relation": rel_type,
                    })
        return relations

    async def auto_extract(self, graph, text: str, source_id: str = None) -> dict:
        """Auto-extract entities and relations and add to graph."""
        from jarvis.brain.memory.graph import Node, Edge

        entities = self.extract_entities(text)
        relations = self.extract_relations(text)

        created_nodes = 0
        created_edges = 0

        # Add entities as nodes
        for ent in entities:
            node = Node(
                id=ent["id"],
                label=ent["value"],
                type=ent["type"],
                content=ent["value"],
            )
            await graph.add_node(node)
            created_nodes += 1

        # Add relations as edges
        for rel in relations:
            source_id_rel = f"concept_{re.sub(r'[^a-zA-Z0-9]', '_', rel['source']).lower()[:50]}"
            target_id_rel = f"concept_{re.sub(r'[^a-zA-Z0-9]', '_', rel['target']).lower()[:50]}"

            # Ensure nodes exist
            for nid, label in [(source_id_rel, rel["source"]), (target_id_rel, rel["target"])]:
                existing = await graph.get_node(nid)
                if not existing:
                    await graph.add_node(Node(id=nid, label=label, type="concept"))

            await graph.add_edge(Edge(
                source=source_id_rel,
                target=target_id_rel,
                relation=rel["relation"],
            ))
            created_edges += 1

        return {
            "ok": True,
            "entities_extracted": len(entities),
            "relations_extracted": len(relations),
            "nodes_created": created_nodes,
            "edges_created": created_edges,
        }


# Module-level instances (initialized lazily with graph)
_graph_analyzer = None
_entity_extractor = EntityExtractor()


def get_graph_analyzer(graph):
    global _graph_analyzer
    if _graph_analyzer is None or _graph_analyzer._graph is not graph:
        _graph_analyzer = GraphAnalyzer(graph)
    return _graph_analyzer


def get_entity_extractor():
    return _entity_extractor
