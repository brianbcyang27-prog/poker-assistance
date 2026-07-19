"""Second brain semantic search engine."""
import logging
import time
from collections import defaultdict
from collections import deque
from typing import Any, Dict, List, Optional, Set

from jarvis.brain.memory.graph import KnowledgeGraph, Node, Edge

from .models import SearchQuery, SearchResult, SearchStats

logger = logging.getLogger(__name__)

# Importance weighting for scoring
_IMPORTANCE_WEIGHT = {"temporary": 0.25, "useful": 0.5, "important": 0.75, "permanent": 1.0}


class SecondBrainSearch:
    """Semantic search over the knowledge graph."""

    def __init__(self, graph: KnowledgeGraph) -> None:
        self._graph = graph
        self._total_searches = 0
        self._total_results = 0
        self._query_counts: Dict[str, int] = defaultdict(int)
        self._mode_counts: Dict[str, int] = defaultdict(int)

    # ------------------------------------------------------------------
    # Main search
    # ------------------------------------------------------------------

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Dispatch to the appropriate search mode."""
        self._total_searches += 1
        self._mode_counts[query.mode] += 1
        if query.text:
            self._query_counts[query.text.lower()] += 1

        if query.mode == "keyword":
            results = await self.keyword_search(
                query.text, query.entity_types, query.limit
            )
        elif query.mode == "graph":
            results = await self.graph_search(query.text, query.limit)
        elif query.mode == "hybrid":
            results = await self.hybrid_search(query.text, query.limit)
        else:
            results = await self.keyword_search(
                query.text, query.entity_types, query.limit
            )

        results = self._apply_filters(results, query)
        results = self.rank_results(results, query)
        self._total_results += len(results)
        return results[: query.limit]

    # ------------------------------------------------------------------
    # Search modes
    # ------------------------------------------------------------------

    async def keyword_search(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Match nodes by name or content substring."""
        conn = self._graph._get_conn()
        query_lower = text.lower()
        results: List[SearchResult] = []

        rows = conn.execute("SELECT * FROM nodes").fetchall()
        for row in rows:
            node = Node(
                id=row["id"],
                label=row["label"],
                type=row["type"],
                content=row["content"] or "",
                metadata=row["metadata"] or "{}",
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            if entity_types and node.type not in entity_types:
                continue

            name_match = query_lower in node.label.lower()
            content_match = query_lower in node.content.lower()
            if not name_match and not content_match:
                continue

            reasons: List[str] = []
            if name_match:
                reasons.append(f"Name matches '{text}'")
            if content_match:
                reasons.append(f"Content mentions '{text}'")

            score = 0.8 if name_match else 0.5
            related = await self._get_neighbor_ids(node.id)

            results.append(SearchResult(
                id=node.id,
                name=node.label,
                entity_type=node.type,
                description=node.content[:200],
                score=score,
                match_reasons=reasons,
                related_entities=related,
            ))

        return results[:limit]

    async def graph_search(
        self, text: str, limit: int = 20, depth: int = 2
    ) -> List[SearchResult]:
        """BFS from keyword-matched nodes through relationships."""
        seed_results = await self.keyword_search(text, limit=limit)
        if not seed_results:
            return []

        visited: Set[str] = set()
        results: List[SearchResult] = []
        queue: deque = deque()

        for sr in seed_results:
            queue.append((sr, 0))
            visited.add(sr.id)
            results.append(sr)

        conn = self._graph._get_conn()

        while queue and len(results) < limit * 3:
            current, d = queue.popleft()
            if d >= depth:
                continue

            edges = conn.execute(
                "SELECT * FROM edges WHERE source = ? OR target = ?",
                (current.id, current.id),
            ).fetchall()

            for edge in edges:
                neighbor_id = edge["target"] if edge["source"] == current.id else edge["source"]
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)

                nrow = conn.execute(
                    "SELECT * FROM nodes WHERE id = ?", (neighbor_id,)
                ).fetchone()
                if nrow is None:
                    continue

                neighbor = Node(
                    id=nrow["id"],
                    label=nrow["label"],
                    type=nrow["type"],
                    content=nrow["content"] or "",
                    metadata=nrow["metadata"] or "{}",
                    created_at=nrow["created_at"],
                    updated_at=nrow["updated_at"],
                )
                dist_score = max(0.3, 1.0 - (d + 1) * 0.25)
                results.append(SearchResult(
                    id=neighbor.id,
                    name=neighbor.label,
                    entity_type=neighbor.type,
                    description=neighbor.content[:200],
                    score=dist_score,
                    match_reasons=[
                        f"Connected to '{current.name}' via {edge['relation']}"
                    ],
                    related_entities=[current.id],
                ))
                queue.append((neighbor, d + 1))

        return results[:limit]

    async def hybrid_search(
        self, text: str, limit: int = 20
    ) -> List[SearchResult]:
        """Combine keyword and graph results, deduplicate, re-score."""
        kw = await self.keyword_search(text, limit=limit)
        gs = await self.graph_search(text, limit=limit)

        merged: Dict[str, SearchResult] = {}
        for r in kw:
            merged[r.id] = r
        for r in gs:
            if r.id in merged:
                existing = merged[r.id]
                existing.score = max(existing.score, r.score) + 0.1
                existing.match_reasons.extend(r.match_reasons)
            else:
                merged[r.id] = r

        return list(merged.values())[:limit]

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    async def rank_results(
        self, results: List[SearchResult], query: SearchQuery
    ) -> List[SearchResult]:
        """Re-score results using relevance + recency + importance + distance."""
        conn = self._graph._get_conn()
        now = time.time()

        for r in results:
            nrow = conn.execute(
                "SELECT * FROM nodes WHERE id = ?", (r.id,)
            ).fetchone()

            recency = 0.0
            importance = 0.5
            if nrow:
                age_hours = max(1, (now - nrow["updated_at"]) / 3600)
                recency = 1.0 / (1.0 + age_hours * 0.01)
                meta_str = nrow["metadata"] or "{}"
                try:
                    meta = __import__("json").loads(meta_str)
                except Exception:
                    meta = {}
                imp = meta.get("importance", "useful")
                importance = _IMPORTANCE_WEIGHT.get(imp, 0.5)

            relationship_dist = 1.0
            if r.related_entities:
                relationship_dist = 0.7

            r.score = (
                r.score * 0.4
                + recency * 0.2
                + importance * 0.2
                + relationship_dist * 0.2
            )

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    # ------------------------------------------------------------------
    # Context & suggestions
    # ------------------------------------------------------------------

    async def get_context(self, entity_id: str, depth: int = 1) -> dict:
        """Return an entity with its neighborhood for context."""
        conn = self._graph._get_conn()
        nrow = conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (entity_id,)
        ).fetchone()
        if nrow is None:
            return {"error": f"Entity '{entity_id}' not found"}

        entity = {
            "id": nrow["id"],
            "label": nrow["label"],
            "type": nrow["type"],
            "content": nrow["content"],
            "metadata": nrow["metadata"],
        }

        neighbors = await self._get_neighbors_with_edges(entity_id, depth)
        return {"entity": entity, "neighbors": neighbors}

    async def suggest_related(
        self, entity_id: str, limit: int = 5
    ) -> List[SearchResult]:
        """Suggest entities related to the given entity."""
        conn = self._graph._get_conn()
        nrow = conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (entity_id,)
        ).fetchone()
        if nrow is None:
            return []

        edges = conn.execute(
            "SELECT * FROM edges WHERE source = ? OR target = ?",
            (entity_id, entity_id),
        ).fetchall()

        results: List[SearchResult] = []
        for edge in edges:
            neighbor_id = edge["target"] if edge["source"] == entity_id else edge["source"]
            nrow2 = conn.execute(
                "SELECT * FROM nodes WHERE id = ?", (neighbor_id,)
            ).fetchone()
            if nrow2 is None:
                continue
            results.append(SearchResult(
                id=nrow2["id"],
                name=nrow2["label"],
                entity_type=nrow2["type"],
                description=(nrow2["content"] or "")[:200],
                score=edge["weight"],
                match_reasons=[f"Connected via {edge['relation']}"],
                related_entities=[entity_id],
            ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    async def get_stats(self) -> SearchStats:
        """Return search usage statistics."""
        avg = (
            self._total_results / self._total_searches
            if self._total_searches
            else 0.0
        )
        top = sorted(
            self._query_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
        return SearchStats(
            total_searches=self._total_searches,
            avg_results=round(avg, 2),
            top_queries=[{"query": q, "count": c} for q, c in top],
            search_modes_used=dict(self._mode_counts),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_neighbor_ids(self, node_id: str) -> List[str]:
        conn = self._graph._get_conn()
        rows = conn.execute(
            "SELECT target FROM edges WHERE source = ? "
            "UNION SELECT source FROM edges WHERE target = ?",
            (node_id, node_id),
        ).fetchall()
        return [r[0] for r in rows]

    async def _get_neighbors_with_edges(
        self, node_id: str, depth: int = 1
    ) -> List[dict]:
        conn = self._graph._get_conn()
        visited: Set[str] = {node_id}
        result: List[dict] = []
        queue: deque = deque([(node_id, 0)])

        while queue:
            current_id, d = queue.popleft()
            if d >= depth:
                continue

            edges = conn.execute(
                "SELECT * FROM edges WHERE source = ? OR target = ?",
                (current_id, current_id),
            ).fetchall()

            for edge in edges:
                neighbor_id = edge["target"] if edge["source"] == current_id else edge["source"]
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)

                nrow = conn.execute(
                    "SELECT * FROM nodes WHERE id = ?", (neighbor_id,)
                ).fetchone()
                if nrow is None:
                    continue
                result.append({
                    "id": nrow["id"],
                    "label": nrow["label"],
                    "type": nrow["type"],
                    "relation": edge["relation"],
                    "distance": d + 1,
                })
                queue.append((neighbor_id, d + 1))

        return result

    def _apply_filters(
        self, results: List[SearchResult], query: SearchQuery
    ) -> List[SearchResult]:
        if query.entity_types:
            results = [
                r for r in results if r.entity_type in query.entity_types
            ]
        if query.min_confidence > 0:
            results = [
                r for r in results
                if r.metadata.get("confidence", 1.0) >= query.min_confidence
            ]
        return results
