"""SQLite-backed KnowledgeGraph for the Second Brain."""
import json
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import (
    Entity,
    Relationship,
    EntityCluster,
    GraphStats,
    ImportanceLevel,
)

MEMORY_DIR = Path("memory_store")
MEMORY_DIR.mkdir(exist_ok=True)


class KnowledgeGraph:
    """SQLite-backed knowledge graph with entities, relationships, and cluster queries."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(MEMORY_DIR / "second_brain.db")
        self._conn: Optional[sqlite3.Connection] = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._init_tables()
        return self._conn

    def _init_tables(self) -> None:
        conn = self._conn
        conn.executescript("""
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

            CREATE TABLE IF NOT EXISTS relationships (
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
            CREATE INDEX IF NOT EXISTS idx_entities_importance ON entities(importance);
            CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id);
            CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id);
            CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(relation_type);
        """)
        conn.commit()

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        d = dict(row)
        d["source_memories"] = json.loads(d["source_memories"])
        d["metadata"] = json.loads(d["metadata"])
        return Entity(**d)

    def _row_to_relationship(self, row: sqlite3.Row) -> Relationship:
        d = dict(row)
        d["metadata"] = json.loads(d["metadata"])
        return Relationship(**d)

    async def add_entity(self, entity: Entity) -> dict:
        conn = self._get_conn()
        now = time.time()
        if not entity.created_at:
            entity.created_at = now
        entity.updated_at = now
        conn.execute(
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
        conn.commit()
        return {"ok": True, "id": entity.id}

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
        return self._row_to_entity(row) if row else None

    async def update_entity(self, entity: Entity) -> dict:
        entity.updated_at = time.time()
        conn = self._get_conn()
        conn.execute(
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
        conn.commit()
        return {"ok": True, "id": entity.id}

    async def delete_entity(self, entity_id: str) -> dict:
        conn = self._get_conn()
        conn.execute("DELETE FROM relationships WHERE source_id=? OR target_id=?", (entity_id, entity_id))
        conn.execute("DELETE FROM entities WHERE id=?", (entity_id,))
        conn.commit()
        return {"ok": True, "deleted": entity_id}

    async def add_relationship(self, relationship: Relationship) -> dict:
        conn = self._get_conn()
        if not relationship.created_at:
            relationship.created_at = time.time()
        conn.execute(
            "INSERT OR REPLACE INTO relationships "
            "(source_id, target_id, relation_type, weight, description, confidence, metadata, created_at) "
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
        conn.commit()
        return {"ok": True}

    async def get_relationships(
        self,
        entity_id: Optional[str] = None,
        relation_type: Optional[str] = None,
        direction: str = "both",
    ) -> List[Relationship]:
        conn = self._get_conn()
        clauses: List[str] = []
        params: List[Any] = []

        if entity_id:
            if direction == "outgoing":
                clauses.append("source_id = ?")
                params.append(entity_id)
            elif direction == "incoming":
                clauses.append("target_id = ?")
                params.append(entity_id)
            else:
                clauses.append("(source_id = ? OR target_id = ?)")
                params.extend([entity_id, entity_id])

        if relation_type:
            clauses.append("relation_type = ?")
            params.append(relation_type)

        where = " AND ".join(clauses) if clauses else "1=1"
        rows = conn.execute(f"SELECT * FROM relationships WHERE {where}", params).fetchall()
        return [self._row_to_relationship(r) for r in rows]

    async def delete_relationship(
        self, source_id: str, target_id: str, relation_type: str
    ) -> dict:
        conn = self._get_conn()
        conn.execute(
            "DELETE FROM relationships WHERE source_id=? AND target_id=? AND relation_type=?",
            (source_id, target_id, relation_type),
        )
        conn.commit()
        return {"ok": True, "deleted": f"{source_id}->{target_id}:{relation_type}"}

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        importance: Optional[str] = None,
        limit: int = 20,
    ) -> List[Entity]:
        conn = self._get_conn()
        clauses: List[str] = ["(name LIKE ? OR description LIKE ?)"]
        params: List[Any] = [f"%{query}%", f"%{query}%"]

        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if importance:
            clauses.append("importance = ?")
            params.append(importance)

        params.append(limit)
        where = " AND ".join(clauses)
        rows = conn.execute(
            f"SELECT * FROM entities WHERE {where} LIMIT ?", params
        ).fetchall()
        return [self._row_to_entity(r) for r in rows]

    async def get_neighbors(
        self, entity_id: str, depth: int = 1, direction: str = "both"
    ) -> Dict[str, Any]:
        conn = self._get_conn()
        visited: set = set()
        result_entities: List[dict] = []
        result_relationships: List[dict] = []

        queue: List[tuple] = [(entity_id, 0)]
        visited.add(entity_id)

        while queue:
            current_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue

            if direction in ("outgoing", "both"):
                rows = conn.execute(
                    "SELECT r.*, e.name, e.entity_type FROM relationships r "
                    "JOIN entities e ON r.target_id = e.id WHERE r.source_id = ?",
                    (current_id,),
                ).fetchall()
                for r in rows:
                    d = dict(r)
                    result_relationships.append(d)
                    if d["target_id"] not in visited:
                        visited.add(d["target_id"])
                        result_entities.append(d)
                        queue.append((d["target_id"], current_depth + 1))

            if direction in ("incoming", "both"):
                rows = conn.execute(
                    "SELECT r.*, e.name, e.entity_type FROM relationships r "
                    "JOIN entities e ON r.source_id = e.id WHERE r.target_id = ?",
                    (current_id,),
                ).fetchall()
                for r in rows:
                    d = dict(r)
                    result_relationships.append(d)
                    if d["source_id"] not in visited:
                        visited.add(d["source_id"])
                        result_entities.append(d)
                        queue.append((d["source_id"], current_depth + 1))

        return {"entities": result_entities, "relationships": result_relationships}

    async def get_entity_clusters(
        self, min_weight: float = 0.5, limit: int = 10
    ) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT r.*, "
            "  e1.name as source_name, e1.entity_type as source_type, "
            "  e2.name as target_name, e2.entity_type as target_type "
            "FROM relationships r "
            "JOIN entities e1 ON r.source_id = e1.id "
            "JOIN entities e2 ON r.target_id = e2.id "
            "WHERE r.weight >= ? "
            "ORDER BY r.weight DESC LIMIT ?",
            (min_weight, limit),
        ).fetchall()

        clusters: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            d = dict(r)
            source_name = d["source_name"]
            target_name = d["target_name"]

            for name in (source_name, target_name):
                if name not in clusters:
                    clusters[name] = {"name": name, "entities": set(), "relationships": []}

            clusters[source_name]["entities"].add(d["source_id"])
            clusters[source_name]["entities"].add(d["target_id"])
            clusters[source_name]["relationships"].append(d)

            clusters[target_name]["entities"].add(d["source_id"])
            clusters[target_name]["entities"].add(d["target_id"])
            clusters[target_name]["relationships"].append(d)

        result: List[Dict[str, Any]] = []
        for name, data in clusters.items():
            entity_ids = list(data["entities"])
            entities = []
            for eid in entity_ids[:20]:
                ent_row = conn.execute("SELECT * FROM entities WHERE id=?", (eid,)).fetchone()
                if ent_row:
                    entities.append(self._row_to_entity(ent_row).to_dict())
            result.append({
                "name": name,
                "entities": entities,
                "relationships": data["relationships"],
                "central_entity": entity_ids[0] if entity_ids else None,
            })

        return result

    async def get_by_type(
        self, entity_type: str, limit: int = 50
    ) -> List[Entity]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM entities WHERE entity_type=? ORDER BY confidence DESC LIMIT ?",
            (entity_type, limit),
        ).fetchall()
        return [self._row_to_entity(r) for r in rows]

    async def get_by_importance(
        self, importance: str, limit: int = 50
    ) -> List[Entity]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM entities WHERE importance=? ORDER BY updated_at DESC LIMIT ?",
            (importance, limit),
        ).fetchall()
        return [self._row_to_entity(r) for r in rows]

    async def get_stats(self) -> GraphStats:
        conn = self._get_conn()
        total_entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        total_rels = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]

        type_rows = conn.execute(
            "SELECT entity_type, COUNT(*) as cnt FROM entities GROUP BY entity_type"
        ).fetchall()
        entity_type_counts = {r["entity_type"]: r["cnt"] for r in type_rows}

        rel_type_rows = conn.execute(
            "SELECT relation_type, COUNT(*) as cnt FROM relationships GROUP BY relation_type"
        ).fetchall()
        relationship_type_counts = {r["relation_type"]: r["cnt"] for r in rel_type_rows}

        avg_conf = 0.0
        avg_imp = 0.0
        if total_entities > 0:
            row = conn.execute("SELECT AVG(confidence) as ac FROM entities").fetchone()
            avg_conf = row["ac"] or 0.0

            importance_map = {
                ImportanceLevel.TEMPORARY.value: 1,
                ImportanceLevel.USEFUL.value: 2,
                ImportanceLevel.IMPORTANT.value: 3,
                ImportanceLevel.PERMANENT.value: 4,
            }
            imp_row = conn.execute("SELECT importance FROM entities").fetchall()
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

    async def get_subgraph(
        self, entity_ids: List[str], include_edges: bool = True
    ) -> Dict[str, Any]:
        conn = self._get_conn()
        if not entity_ids:
            return {"entities": [], "relationships": []}

        placeholders = ",".join("?" for _ in entity_ids)
        rows = conn.execute(
            f"SELECT * FROM entities WHERE id IN ({placeholders})", entity_ids
        ).fetchall()
        entities = [self._row_to_entity(r).to_dict() for r in rows]

        relationships: List[dict] = []
        if include_edges:
            rel_rows = conn.execute(
                f"SELECT * FROM relationships WHERE source_id IN ({placeholders}) "
                f"AND target_id IN ({placeholders})",
                entity_ids + entity_ids,
            ).fetchall()
            relationships = [self._row_to_relationship(r).to_dict() for r in rel_rows]

        return {"entities": entities, "relationships": relationships}

    async def to_dict(self) -> Dict[str, Any]:
        conn = self._get_conn()
        entity_rows = conn.execute("SELECT * FROM entities").fetchall()
        entities = [self._row_to_entity(r).to_dict() for r in entity_rows]

        rel_rows = conn.execute("SELECT * FROM relationships").fetchall()
        relationships = [self._row_to_relationship(r).to_dict() for r in rel_rows]

        return {
            "entities": entities,
            "relationships": relationships,
            "count": {
                "entities": len(entities),
                "relationships": len(relationships),
            },
        }

    async def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
