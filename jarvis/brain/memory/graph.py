"""Knowledge graph with nodes, edges, and Obsidian-style bidirectional links."""
import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict

MEMORY_DIR = Path(__file__).parent.parent.parent.parent / "memory_store"
MEMORY_DIR.mkdir(exist_ok=True)


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

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(MEMORY_DIR / "knowledge_graph.db")
        self._conn = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._init_tables()
        return self._conn

    def _init_tables(self):
        conn = self._conn
        conn.executescript("""
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
        """)
        conn.commit()

    async def add_node(self, node: Node) -> dict:
        conn = self._get_conn()
        now = time.time()
        node.created_at = node.created_at or now
        node.updated_at = now
        conn.execute(
            "INSERT OR REPLACE INTO nodes (id, label, type, content, metadata, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node.id, node.label, node.type, node.content, node.metadata, node.created_at, node.updated_at)
        )
        conn.commit()
        return {"ok": True, "id": node.id}

    async def add_edge(self, edge: Edge) -> dict:
        conn = self._get_conn()
        edge.created_at = edge.created_at or time.time()
        conn.execute(
            "INSERT OR REPLACE INTO edges (source, target, relation, weight, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (edge.source, edge.target, edge.relation, edge.weight, edge.metadata, edge.created_at)
        )
        conn.commit()
        return {"ok": True}

    async def get_node(self, node_id: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return dict(row) if row else None

    async def get_neighbors(self, node_id: str, direction: str = "both") -> dict:
        """Get all connected nodes. direction: outgoing, incoming, both."""
        conn = self._get_conn()
        results = {"outgoing": [], "incoming": []}

        if direction in ("outgoing", "both"):
            rows = conn.execute(
                "SELECT e.*, n.label, n.type FROM edges e JOIN nodes n ON e.target = n.id WHERE e.source = ?",
                (node_id,)
            ).fetchall()
            results["outgoing"] = [dict(r) for r in rows]

        if direction in ("incoming", "both"):
            rows = conn.execute(
                "SELECT e.*, n.label, n.type FROM edges e JOIN nodes n ON e.source = n.id WHERE e.target = ?",
                (node_id,)
            ).fetchall()
            results["incoming"] = [dict(r) for r in rows]

        return {"ok": True, "neighbors": results}

    async def search_nodes(self, query: str, node_type: Optional[str] = None, limit: int = 20) -> dict:
        conn = self._get_conn()
        if node_type:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE type = ? AND (label LIKE ? OR content LIKE ?) LIMIT ?",
                (node_type, f"%{query}%", f"%{query}%", limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE label LIKE ? OR content LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()
        return {"ok": True, "results": [dict(r) for r in rows]}

    async def extract_and_link(self, text: str, source_type: str = "conversation") -> dict:
        """Extract [[bidirectional links]] from text and create nodes/edges."""
        import re
        links = re.findall(r'\[\[(.+?)\]\]', text)
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
            "details": created_edges
        }

    async def get_graph_data(self, limit: int = 100) -> dict:
        """Get nodes and edges for visualization."""
        conn = self._get_conn()
        nodes = conn.execute("SELECT * FROM nodes LIMIT ?", (limit,)).fetchall()
        edges = conn.execute(
            "SELECT e.*, s.label as source_label, t.label as target_label "
            "FROM edges e "
            "JOIN nodes s ON e.source = s.id "
            "JOIN nodes t ON e.target = t.id "
            "LIMIT ?", (limit * 3,)
        ).fetchall()
        return {
            "ok": True,
            "nodes": [dict(n) for n in nodes],
            "edges": [dict(e) for e in edges]
        }

    async def get_stats(self) -> dict:
        conn = self._get_conn()
        node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        types = conn.execute("SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type").fetchall()
        return {
            "ok": True,
            "nodes": node_count,
            "edges": edge_count,
            "notes": note_count,
            "types": {r["type"]: r["cnt"] for r in types}
        }

    async def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


graph = KnowledgeGraph()
