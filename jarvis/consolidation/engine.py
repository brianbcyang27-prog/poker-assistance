"""Memory consolidation engine for deduplication, merging, and cleanup."""
import asyncio
import json
import time
from typing import List, Optional, Dict, Any

from jarvis.consolidation.models import (
    ConsolidationAction,
    ConsolidationResult,
    DuplicateGroup,
    MergeCandidate,
)


class ConsolidationEngine:
    """Engine for consolidating knowledge graph memories."""

    _importance_order = {
        "permanent": 4,
        "important": 3,
        "useful": 2,
        "temporary": 1,
    }

    def __init__(self, knowledge_graph):
        self.knowledge_graph = knowledge_graph

    async def consolidate(self) -> ConsolidationResult:
        result = ConsolidationResult()

        duplicates = await self.find_duplicates()
        for group in duplicates:
            if len(group.entity_ids) > 1:
                primary = group.entity_ids[0]
                for secondary in group.entity_ids[1:]:
                    await self.merge(primary, secondary)
                    result.memories_merged += 1
                result.actions_taken.append({
                    "action": ConsolidationAction.MERGE.value,
                    "group": group.entity_ids,
                    "reason": group.reason,
                })
        result.duplicates_removed = await self.deduplicate()

        strengthened = await self.strengthen_recent()
        result.memories_strengthened = strengthened
        if strengthened:
            result.actions_taken.append({
                "action": ConsolidationAction.STRENGTHEN.value,
                "count": strengthened,
            })

        forgotten = await self.forget_weak()
        result.memories_forgotten = forgotten
        if forgotten:
            result.actions_taken.append({
                "action": ConsolidationAction.FORGET.value,
                "count": forgotten,
            })

        return result

    async def find_duplicates(self) -> List[DuplicateGroup]:
        duplicates = []
        graph_data = await self.knowledge_graph.get_graph_data(limit=10000)
        nodes = graph_data.get("nodes", [])

        seen = {}
        for node in nodes:
            key = node.get("label", "").lower().strip()
            if key in seen:
                duplicates.append(DuplicateGroup(
                    entity_ids=[seen[key], node["id"]],
                    reason=f"Duplicate label: {node.get('label', '')}",
                    confidence=0.95,
                ))
            else:
                seen[key] = node["id"]

        return duplicates

    async def merge(self, primary_id: str, secondary_id: str) -> dict:
        primary = await self.knowledge_graph.get_node(primary_id)
        secondary = await self.knowledge_graph.get_node(secondary_id)

        if not primary or not secondary:
            return {"ok": False, "error": "entity not found"}

        from jarvis.brain.memory.graph import Node

        merged_content = primary.get("content", "") or ""
        secondary_content = secondary.get("content", "") or ""
        if secondary_content and merged_content.endswith("."):
            merged_content += " "
        elif secondary_content:
            merged_content += " "
        merged_content += secondary_content

        merged_metadata = {}
        try:
            pm = json.loads(primary.get("metadata", "{}"))
            merged_metadata.update(pm)
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            sm = json.loads(secondary.get("metadata", "{}"))
            merged_metadata.update(sm)
        except (json.JSONDecodeError, TypeError):
            pass

        merged_node = Node(
            id=primary_id,
            label=primary.get("label", secondary.get("label", "")),
            type=primary.get("type", secondary.get("type", "concept")),
            content=merged_content,
            metadata=json.dumps(merged_metadata),
        )

        await self.knowledge_graph.add_node(merged_node)

        neighbors = await self.knowledge_graph.get_neighbors(secondary_id)
        from jarvis.brain.memory.graph import Edge

        for edge in neighbors.get("neighbors", {}).get("outgoing", []):
            await self.knowledge_graph.add_edge(Edge(
                source=primary_id,
                target=edge["target"],
                relation=edge["relation"],
                weight=edge.get("weight", 1.0),
                metadata=json.dumps({"merged_from": secondary_id}),
            ))

        for edge in neighbors.get("neighbors", {}).get("incoming", []):
            await self.knowledge_graph.add_edge(Edge(
                source=edge["source"],
                target=primary_id,
                relation=edge["relation"],
                weight=edge.get("weight", 1.0),
                metadata=json.dumps({"merged_from": secondary_id}),
            ))

        return {"ok": True, "merged": secondary_id, "into": primary_id}

    async def deduplicate(self) -> int:
        duplicates = await self.find_duplicates()
        removed = 0

        for group in duplicates:
            if len(group.entity_ids) > 1:
                primary = group.entity_ids[0]
                for secondary in group.entity_ids[1:]:
                    result = await self.merge(primary, secondary)
                    if result.get("ok"):
                        removed += 1

        return removed

    async def strengthen_recent(self, hours: int = 24, delta: float = 0.1) -> int:
        count = 0
        cutoff = time.time() - (hours * 3600)
        graph_data = await self.knowledge_graph.get_graph_data(limit=10000)

        for node in graph_data.get("nodes", []):
            created = node.get("created_at", 0) or 0
            if created >= cutoff:
                try:
                    from jarvis.brain.memory.graph import Node

                    metadata = {}
                    try:
                        metadata = json.loads(node.get("metadata", "{}"))
                    except (json.JSONDecodeError, TypeError):
                        pass

                    confidence = float(metadata.get("confidence", 0.7))
                    metadata["confidence"] = min(1.0, confidence + delta)
                    metadata["strengthened_at"] = time.time()

                    updated = Node(
                        id=node["id"],
                        label=node.get("label", ""),
                        type=node.get("type", "concept"),
                        content=node.get("content", ""),
                        metadata=json.dumps(metadata),
                        created_at=node.get("created_at", 0),
                        updated_at=time.time(),
                    )
                    await self.knowledge_graph.add_node(updated)
                    count += 1
                except Exception:
                    pass

        return count

    async def forget_weak(self, threshold: float = 0.2) -> int:
        count = 0
        graph_data = await self.knowledge_graph.get_graph_data(limit=10000)

        for node in graph_data.get("nodes", []):
            try:
                metadata = json.loads(node.get("metadata", "{}"))
            except (json.JSONDecodeError, TypeError):
                metadata = {}

            confidence = float(metadata.get("confidence", 0.7))
            if confidence < threshold:
                conn = self.knowledge_graph._get_conn()
                conn.execute("DELETE FROM edges WHERE source = ? OR target = ?", (node["id"], node["id"]))
                conn.execute("DELETE FROM nodes WHERE id = ?", (node["id"],))
                conn.commit()
                count += 1

        return count

    async def summarize_cluster(self, entity_ids: List[str]) -> str:
        parts = []
        for eid in entity_ids:
            node = await self.knowledge_graph.get_node(eid)
            if node:
                parts.append(f"{node.get('label', eid)}: {node.get('content', '')[:200]}")
        return " ".join(parts) if parts else ""

    async def get_stats(self) -> dict:
        kg_stats = await self.knowledge_graph.get_stats()
        return {
            "ok": True,
            "nodes": kg_stats.get("nodes", 0),
            "edges": kg_stats.get("edges", 0),
            "notes": kg_stats.get("notes", 0),
            "types": kg_stats.get("types", {}),
        }
