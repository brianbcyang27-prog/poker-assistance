"""Knowledge graph with nodes, edges, entities, relationships, and Obsidian-style
bidirectional links.

This module unifies two previously separate graph systems:
  - Node/Edge — lightweight graph (knowledge_graph.db) for wiki-link extraction, RAG,
    and visualization
  - Entity/Relationship — rich semantic graph (same database, entities/relationships
    tables) for the MemoryManager "second brain" API (add_entity, search_entities,
    delete_entity)
"""

import json
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import aiosqlite

MEMORY_DIR = Path(__file__).parent.parent.parent.parent / "memory_store"
MEMORY_DIR.mkdir(exist_ok=True)


# ── Semantic Entity / Relationship Models (unified from knowledge/) ──────────


class EntityType(StrEnum):
    PERSON = "person"
    PROJECT = "project"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    SKILL = "skill"
    CONCEPT = "concept"
    DECISION = "decision"
    GOAL = "goal"
    TASK = "task"
    DOCUMENT = "document"
    CODEBASE = "codebase"
    DEVICE = "device"
    LOCATION = "location"
    EVENT = "event"
    RESOURCE = "resource"


class ImportanceLevel(StrEnum):
    TEMPORARY = "temporary"
    USEFUL = "useful"
    IMPORTANT = "important"
    PERMANENT = "permanent"


class RelationType(StrEnum):
    CREATED = "created"
    USES = "uses"
    REQUIRES = "requires"
    INSPIRED_BY = "inspired_by"
    CAUSED = "caused"
    IMPROVED_BY = "improved_by"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    FOLLOWS = "follows"
    LEADS_TO = "leads_to"
    INFLUENCES = "influences"
    CONTAINS = "contains"
    MENTIONS = "mentions"
    WORKS_WITH = "works_with"


@dataclass
class Entity:
    id: str = ""
    name: str = ""
    entity_type: str = "concept"
    description: str = ""
    importance: str = "useful"
    confidence: float = 0.8
    source_memories: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.entity_type}_{hash(self.name) & 0xFFFFFFFF:08x}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "description": self.description,
            "importance": self.importance,
            "confidence": self.confidence,
            "source_memories": self.source_memories,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Relationship:
    source_id: str = ""
    target_id: str = ""
    relation_type: str = "related_to"
    weight: float = 1.0
    description: str = ""
    confidence: float = 0.8
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "weight": self.weight,
            "description": self.description,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class EntityCluster:
    name: str = ""
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    central_entity: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "central_entity": self.central_entity,
        }


@dataclass
class GraphStats:
    total_entities: int = 0
    total_relationships: int = 0
    entity_type_counts: dict[str, int] = field(default_factory=dict)
    relationship_type_counts: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_importance: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships,
            "entity_type_counts": self.entity_type_counts,
            "relationship_type_counts": self.relationship_type_counts,
            "avg_confidence": self.avg_confidence,
            "avg_importance": self.avg_importance,
        }


# ── Lightweight Node / Edge Models ──────────────────────────────────────────


@dataclass
class Node:
    id: str
    label: str
    type: str  # concept, entity, note, conversation, decision, code
    content: str = ""
    metadata: str = "{}"
    created_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class Edge:
    source: str
    target: str
    relation: str  # related_to, contains, depends_on, created_from, references
    weight: float = 1.0
    metadata: str = "{}"
    created_at: float = 0.0


class KnowledgeGraph:
    """SQLite-backed knowledge graph with bidirectional linking."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(MEMORY_DIR / "knowledge_graph.db")
        self._conn: aiosqlite.Connection | None = None

    async def _get_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._init_tables()
        return self._conn

    async def _init_tables(self):
        conn = self._conn
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS edges (
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                metadata TEXT DEFAULT '{}',
                created_at REAL DEFAULT 0,
                PRIMARY KEY (source, target, relation),
                FOREIGN KEY (source) REFERENCES nodes(id),
                FOREIGN KEY (target) REFERENCES nodes(id)
            );

            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label);

            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                description TEXT DEFAULT '',
                importance TEXT DEFAULT 'useful',
                confidence REAL DEFAULT 0.8,
                source_memories TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}',
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS entity_relationships (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                description TEXT DEFAULT '',
                confidence REAL DEFAULT 0.8,
                metadata TEXT DEFAULT '{}',
                created_at REAL DEFAULT 0,
                PRIMARY KEY (source_id, target_id, relation_type),
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            );

            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
            CREATE INDEX IF NOT EXISTS idx_er_source ON entity_relationships(source_id);
            CREATE INDEX IF NOT EXISTS idx_er_target ON entity_relationships(target_id);
        """)
        await conn.commit()

    async def add_node(self, node: Node) -> dict:
        conn = await self._get_conn()
        now = time.time()
        node.created_at = node.created_at or now
        node.updated_at = now
        await conn.execute(
            "INSERT OR REPLACE INTO nodes (id, label, type, content, metadata, created_at, "
            "updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                node.id,
                node.label,
                node.type,
                node.content,
                node.metadata,
                node.created_at,
                node.updated_at,
            ),
        )
        await conn.commit()
        return {"ok": True, "id": node.id}

    async def add_edge(self, edge: Edge) -> dict:
        conn = await self._get_conn()
        edge.created_at = edge.created_at or time.time()
        await conn.execute(
            "INSERT OR REPLACE INTO edges (source, target, relation, weight, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (edge.source, edge.target, edge.relation, edge.weight, edge.metadata, edge.created_at),
        )
        await conn.commit()
        return {"ok": True}

    async def get_node(self, node_id: str) -> dict | None:
        conn = await self._get_conn()
        cursor = await conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_neighbors(self, node_id: str, direction: str = "both") -> dict:
        """Get all connected nodes. direction: outgoing, incoming, both."""
        conn = await self._get_conn()
        results = {"outgoing": [], "incoming": []}

        if direction in ("outgoing", "both"):
            cursor = await conn.execute(
                "SELECT e.*, n.label, n.type FROM edges e JOIN nodes n "
                "ON e.target = n.id WHERE e.source = ?",
                (node_id,),
            )
            rows = await cursor.fetchall()
            results["outgoing"] = [dict(r) for r in rows]

        if direction in ("incoming", "both"):
            cursor = await conn.execute(
                "SELECT e.*, n.label, n.type FROM edges e JOIN nodes n "
                "ON e.source = n.id WHERE e.target = ?",
                (node_id,),
            )
            rows = await cursor.fetchall()
            results["incoming"] = [dict(r) for r in rows]

        return {"ok": True, "neighbors": results}

    async def search_nodes(self, query: str, node_type: str | None = None, limit: int = 20) -> dict:
        conn = await self._get_conn()
        if node_type:
            cursor = await conn.execute(
                "SELECT * FROM nodes WHERE type = ? AND (label LIKE ? OR content LIKE ?) LIMIT ?",
                (node_type, f"%{query}%", f"%{query}%", limit),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM nodes WHERE label LIKE ? OR content LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit),
            )
        rows = await cursor.fetchall()
        return {"ok": True, "results": [dict(r) for r in rows]}

    async def extract_and_link(self, text: str, source_type: str = "conversation") -> dict:
        """Extract [[bidirectional links]] from text and create nodes/edges."""
        import re

        links = re.findall(r"\[\[(.+?)\]\]", text)
        created_nodes = []
        created_edges = []

        # Create a node for this content
        content_hash = str(hash(text[:200]))[:12]
        source_id = f"{source_type}_{content_hash}"

        for link_text in links:
            node_id = f"concept_{link_text.lower().replace(' ', '_').replace('/', '_')}"
            node = Node(id=node_id, label=link_text, type="concept")
            await self.add_node(node)
            created_nodes.append(node_id)

            # Create bidirectional edge
            await self.add_edge(Edge(source=source_id, target=node_id, relation="references"))
            await self.add_edge(Edge(source=node_id, target=source_id, relation="referenced_by"))
            created_edges.append({"from": source_id, "to": node_id, "label": "references"})

        return {
            "ok": True,
            "source_id": source_id,
            "links_found": len(links),
            "nodes_created": len(created_nodes),
            "edges_created": len(created_edges),
            "details": created_edges,
        }

    async def get_graph_data(self, limit: int = 100) -> dict:
        """Get nodes and edges for visualization."""
        conn = await self._get_conn()
        cursor = await conn.execute("SELECT * FROM nodes LIMIT ?", (limit,))
        nodes = await cursor.fetchall()
        cursor = await conn.execute(
            "SELECT e.*, s.label as source_label, t.label as target_label "
            "FROM edges e "
            "JOIN nodes s ON e.source = s.id "
            "JOIN nodes t ON e.target = t.id "
            "LIMIT ?",
            (limit * 3,),
        )
        edges = await cursor.fetchall()
        return {"ok": True, "nodes": [dict(n) for n in nodes], "edges": [dict(e) for e in edges]}

    async def get_node_stats(self) -> dict:
        """Get node/edge statistics (lightweight graph)."""
        conn = await self._get_conn()
        cursor = await conn.execute("SELECT COUNT(*) FROM nodes")
        node_count = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM edges")
        edge_count = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM notes")
        note_count = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type")
        types = await cursor.fetchall()
        return {
            "ok": True,
            "nodes": node_count,
            "edges": edge_count,
            "notes": note_count,
            "types": {r["type"]: r["cnt"] for r in types},
        }

    # ── Entity / Relationship API (MemoryManager "second brain" integration) ──

    def _row_to_entity(self, row: aiosqlite.Row) -> Entity:
        d = dict(row)
        d["source_memories"] = json.loads(d["source_memories"])
        d["metadata"] = json.loads(d["metadata"])
        return Entity(**d)

    def _row_to_relationship(self, row: aiosqlite.Row) -> Relationship:
        d = dict(row)
        d["metadata"] = json.loads(d["metadata"])
        return Relationship(**d)

    async def add_entity(self, entity: Entity) -> dict:
        """Store an entity (rich semantic graph)."""
        conn = await self._get_conn()
        now = time.time()
        if not entity.created_at:
            entity.created_at = now
        entity.updated_at = now
        await conn.execute(
            "INSERT OR REPLACE INTO entities "
            "(id, name, entity_type, description, importance, confidence, "
            "source_memories, metadata, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entity.id,
                entity.name,
                entity.entity_type,
                entity.description,
                entity.importance,
                entity.confidence,
                json.dumps(entity.source_memories),
                json.dumps(entity.metadata),
                entity.created_at,
                entity.updated_at,
            ),
        )
        await conn.commit()
        return {"ok": True, "id": entity.id}

    async def get_entity(self, entity_id: str) -> Entity | None:
        conn = await self._get_conn()
        cursor = await conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
        row = await cursor.fetchone()
        return self._row_to_entity(row) if row else None

    async def update_entity(self, entity: Entity) -> dict:
        entity.updated_at = time.time()
        conn = await self._get_conn()
        await conn.execute(
            "UPDATE entities SET name=?, entity_type=?, description=?, importance=?, "
            "confidence=?, source_memories=?, metadata=?, updated_at=? WHERE id=?",
            (
                entity.name,
                entity.entity_type,
                entity.description,
                entity.importance,
                entity.confidence,
                json.dumps(entity.source_memories),
                json.dumps(entity.metadata),
                entity.updated_at,
                entity.id,
            ),
        )
        await conn.commit()
        return {"ok": True, "id": entity.id}

    async def delete_entity(self, entity_id: str) -> dict:
        conn = await self._get_conn()
        await conn.execute(
            "DELETE FROM entity_relationships WHERE source_id=? OR target_id=?",
            (entity_id, entity_id),
        )
        await conn.execute("DELETE FROM entities WHERE id=?", (entity_id,))
        await conn.commit()
        return {"ok": True, "deleted": entity_id}

    async def add_relationship(self, relationship: Relationship) -> dict:
        conn = await self._get_conn()
        if not relationship.created_at:
            relationship.created_at = time.time()
        await conn.execute(
            "INSERT OR REPLACE INTO entity_relationships "
            "(source_id, target_id, relation_type, weight, description, confidence, "
            "metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                relationship.source_id,
                relationship.target_id,
                relationship.relation_type,
                relationship.weight,
                relationship.description,
                relationship.confidence,
                json.dumps(relationship.metadata),
                relationship.created_at,
            ),
        )
        await conn.commit()
        return {"ok": True}

    async def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        importance: str | None = None,
        limit: int = 20,
    ) -> list[Entity]:
        conn = await self._get_conn()
        clauses: list[str] = ["(name LIKE ? OR description LIKE ?)"]
        params: list[Any] = [f"%{query}%", f"%{query}%"]

        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if importance:
            clauses.append("importance = ?")
            params.append(importance)

        params.append(limit)
        where = " AND ".join(clauses)
        cursor = await conn.execute(f"SELECT * FROM entities WHERE {where} LIMIT ?", params)
        rows = await cursor.fetchall()
        return [self._row_to_entity(r) for r in rows]

    async def get_stats(self) -> GraphStats:
        """Get entity/relationship statistics (semantic graph)."""
        conn = await self._get_conn()

        cursor = await conn.execute("SELECT COUNT(*) as cnt FROM entities")
        total_entities = (await cursor.fetchone())["cnt"]

        cursor = await conn.execute("SELECT COUNT(*) as cnt FROM entity_relationships")
        total_rels = (await cursor.fetchone())["cnt"]

        cursor = await conn.execute(
            "SELECT entity_type, COUNT(*) as cnt FROM entities GROUP BY entity_type"
        )
        type_rows = await cursor.fetchall()
        entity_type_counts = {r["entity_type"]: r["cnt"] for r in type_rows}

        cursor = await conn.execute(
            "SELECT relation_type, COUNT(*) as cnt FROM entity_relationships GROUP BY relation_type"
        )
        rel_type_rows = await cursor.fetchall()
        relationship_type_counts = {r["relation_type"]: r["cnt"] for r in rel_type_rows}

        avg_conf = 0.0
        avg_imp = 0.0
        if total_entities > 0:
            cursor = await conn.execute("SELECT AVG(confidence) as ac FROM entities")
            row = await cursor.fetchone()
            avg_conf = row["ac"] or 0.0

            importance_map = {
                ImportanceLevel.TEMPORARY.value: 1,
                ImportanceLevel.USEFUL.value: 2,
                ImportanceLevel.IMPORTANT.value: 3,
                ImportanceLevel.PERMANENT.value: 4,
            }
            cursor = await conn.execute("SELECT importance FROM entities")
            imp_row = await cursor.fetchall()
            if imp_row:
                imp_vals = [importance_map.get(r["importance"], 2) for r in imp_row]
                avg_imp = sum(imp_vals) / len(imp_vals) if imp_vals else 0.0

        return GraphStats(
            total_entities=total_entities,
            total_relationships=total_rels,
            entity_type_counts=entity_type_counts,
            relationship_type_counts=relationship_type_counts,
            avg_confidence=avg_conf,
            avg_importance=avg_imp,
        )

    async def to_dict(self) -> dict:
        """Export all entities and relationships."""
        conn = await self._get_conn()

        cursor = await conn.execute("SELECT * FROM entities")
        entity_rows = await cursor.fetchall()
        entities = [self._row_to_entity(r).to_dict() for r in entity_rows]

        cursor = await conn.execute("SELECT * FROM entity_relationships")
        rel_rows = await cursor.fetchall()
        relationships = [self._row_to_relationship(r).to_dict() for r in rel_rows]

        return {
            "entities": entities,
            "relationships": relationships,
            "count": {
                "entities": len(entities),
                "relationships": len(relationships),
            },
        }

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None


graph = KnowledgeGraph()
