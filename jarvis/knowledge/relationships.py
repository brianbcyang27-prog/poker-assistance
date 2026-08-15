"""Relationship engine for the Second Brain knowledge graph."""

from collections import deque
from typing import Any

from .graph import KnowledgeGraph
from .models import Relationship


class RelationshipEngine:
    """Manages relationship creation, traversal, strengthening, and suggestion."""

    RELATIONSHIP_SUGGESTIONS: dict[str, list[str]] = {
        "person": ["works_with", "created", "inspired_by", "related_to"],
        "project": ["depends_on", "uses", "created", "part_of", "related_to"],
        "organization": ["works_with", "contains", "related_to"],
        "technology": ["used_by", "depends_on", "requires", "improved_by"],
        "skill": ["used_by", "improved_by", "requires", "related_to"],
        "concept": ["inspired_by", "related_to", "part_of", "influences"],
        "decision": ["caused", "led_to", "influenced_by", "follows"],
        "goal": ["requires", "depends_on", "part_of", "influenced_by"],
        "task": ["depends_on", "follows", "created_by", "uses"],
        "document": ["mentions", "created", "related_to", "part_of"],
        "codebase": ["uses", "depends_on", "contains", "related_to"],
        "device": ["uses", "located_in", "related_to"],
        "location": ["contains", "related_to", "part_of"],
        "event": ["caused", "follows", "inspired_by", "related_to"],
        "resource": ["used_by", "depends_on", "part_of", "related_to"],
    }

    TYPE_COMPATIBILITY: dict[str, set] = {
        "person": {"person", "project", "organization", "skill", "concept", "device"},
        "project": {"project", "technology", "task", "person", "goal", "codebase"},
        "organization": {"person", "project", "organization", "resource"},
        "technology": {"technology", "project", "codebase", "skill", "resource"},
        "skill": {"person", "technology", "goal", "concept"},
        "concept": {"concept", "decision", "goal", "document", "skill"},
        "decision": {"concept", "goal", "task", "person"},
        "goal": {"project", "task", "decision", "skill", "person"},
        "task": {"project", "goal", "person", "technology", "document"},
        "document": {"person", "project", "concept", "event", "organization"},
        "codebase": {"technology", "project", "person", "task"},
        "device": {"person", "location", "technology"},
        "location": {"person", "event", "device", "organization"},
        "event": {"person", "location", "decision", "concept"},
        "resource": {"project", "organization", "technology", "person"},
    }

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relation_type: str = "related_to",
        weight: float = 1.0,
        description: str = "",
        confidence: float = 0.8,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            description=description,
            confidence=confidence,
            metadata=metadata or {},
        )
        result = await self.graph.add_relationship(rel)
        return result

    async def find_path(
        self, source_id: str, target_id: str, max_depth: int = 5
    ) -> list[str] | None:
        if source_id == target_id:
            return [source_id]

        conn = await self.graph._get_conn()
        visited: dict[str, str | None] = {source_id: None}
        queue: deque = deque([(source_id, 0)])

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            cursor = await conn.execute(
                "SELECT target_id FROM relationships WHERE source_id=? "
                "UNION "
                "SELECT source_id FROM relationships WHERE target_id=?",
                (current_id, current_id),
            )
            rows = await cursor.fetchall()

            for row in rows:
                neighbor = row[0]
                if neighbor == target_id:
                    path = [neighbor]
                    node = current_id
                    while node is not None:
                        path.append(node)
                        node = visited[node]
                    path.reverse()
                    return path

                if neighbor not in visited:
                    visited[neighbor] = current_id
                    queue.append((neighbor, depth + 1))

        return None

    async def get_cluster(self, entity_id: str, depth: int = 2) -> dict[str, Any]:
        result = await self.graph.get_neighbors(entity_id, depth=depth)
        conn = await self.graph._get_conn()

        entity_ids: list[str] = []
        for e in result.get("entities", []):
            eid = e.get("id") or e.get("source_id") or e.get("target_id")
            if eid and eid not in entity_ids:
                entity_ids.append(eid)
        if entity_id not in entity_ids:
            entity_ids.insert(0, entity_id)

        entities = []
        for eid in entity_ids:
            cursor = await conn.execute("SELECT * FROM entities WHERE id=?", (eid,))
            row = await cursor.fetchone()
            if row:
                entities.append(self.graph._row_to_entity(row).to_dict())

        return {
            "entities": entities,
            "relationships": result.get("relationships", []),
            "central_entity": entity_id,
        }

    async def suggest_relationships(self, entity_id: str) -> list[dict[str, Any]]:
        entity = await self.graph.get_entity(entity_id)
        if not entity:
            return []

        conn = await self.graph._get_conn()
        compatible_types = self.TYPE_COMPATIBILITY.get(entity.entity_type, set())

        if not compatible_types:
            return []

        suggestions: list[dict[str, Any]] = []
        type_placeholders = ",".join("?" for _ in compatible_types)

        cursor = await conn.execute(
            f"SELECT * FROM entities WHERE entity_type IN ({type_placeholders}) "
            f"AND id != ? ORDER BY confidence DESC LIMIT 20",
            list(compatible_types) + [entity_id],
        )
        rows = await cursor.fetchall()

        existing = set()
        cursor = await conn.execute(
            "SELECT target_id FROM relationships WHERE source_id=?", (entity_id,)
        )
        rel_rows = await cursor.fetchall()
        for r in rel_rows:
            existing.add(r[0])

        for row in rows:
            candidate = self.graph._row_to_entity(row)
            if candidate.id in existing:
                continue

            possible_rels = self.RELATIONSHIP_SUGGESTIONS.get(entity.entity_type, ["related_to"])
            suggestions.append(
                {
                    "entity_id": candidate.id,
                    "name": candidate.name,
                    "entity_type": candidate.entity_type,
                    "suggested_relation_types": possible_rels,
                }
            )

        return suggestions

    async def strengthen(self, source_id: str, target_id: str, delta: float = 0.1) -> dict:
        conn = await self.graph._get_conn()
        cursor = await conn.execute(
            "SELECT * FROM relationships WHERE source_id=? AND target_id=?",
            (source_id, target_id),
        )
        rows = await cursor.fetchall()

        updated = 0
        for row in rows:
            new_weight = min(10.0, row["weight"] + delta)
            await conn.execute(
                "UPDATE relationships SET weight=? "
                "WHERE source_id=? AND target_id=? AND relation_type=?",
                (new_weight, source_id, target_id, row["relation_type"]),
            )
            updated += 1

        await conn.commit()
        return {"ok": True, "updated": updated, "source_id": source_id, "target_id": target_id}

    async def weaken(self, source_id: str, target_id: str, delta: float = 0.1) -> dict:
        conn = await self.graph._get_conn()
        cursor = await conn.execute(
            "SELECT * FROM relationships WHERE source_id=? AND target_id=?",
            (source_id, target_id),
        )
        rows = await cursor.fetchall()

        deleted = 0
        updated = 0
        for row in rows:
            new_weight = row["weight"] - delta
            if new_weight <= 0:
                await conn.execute(
                    "DELETE FROM relationships "
                    "WHERE source_id=? AND target_id=? AND relation_type=?",
                    (source_id, target_id, row["relation_type"]),
                )
                deleted += 1
            else:
                await conn.execute(
                    "UPDATE relationships SET weight=? "
                    "WHERE source_id=? AND target_id=? AND relation_type=?",
                    (new_weight, source_id, target_id, row["relation_type"]),
                )
                updated += 1

        await conn.commit()
        return {
            "ok": True,
            "updated": updated,
            "deleted": deleted,
            "source_id": source_id,
            "target_id": target_id,
        }

    async def get_strongest(self, n: int = 10) -> list[dict[str, Any]]:
        conn = await self.graph._get_conn()
        cursor = await conn.execute(
            "SELECT r.*, e1.name as source_name, e2.name as target_name "
            "FROM relationships r "
            "JOIN entities e1 ON r.source_id = e1.id "
            "JOIN entities e2 ON r.target_id = e2.id "
            "ORDER BY r.weight DESC LIMIT ?",
            (n,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
