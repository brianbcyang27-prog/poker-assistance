"""Pluggable Memory Architecture — Swappable memory backends.

Provides a unified MemoryProvider interface. Current: SQLite.
Future: Mem0, Hindsight, Vector DB, Cloud, Local Encrypted.

Usage:
    from jarvis.brain.memory_provider import memory, MemoryQuery

    # Store
    await memory.store("conversation", {"user": "hello", "response": "hi"})

    # Retrieve
    results = await memory.retrieve(MemoryQuery(
        type="conversation",
        text="hello",
        limit=5,
    ))

    # Search
    results = await memory.search("blockflow project")
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path
from enum import Enum

log = logging.getLogger("jarvis.memory")


class MemoryType(str, Enum):
    CONVERSATION = "conversation"
    MISSION = "mission"
    TASK = "task"
    TERMINAL = "terminal"
    CODE = "code"
    DEMO = "demo"
    DOCUMENT = "document"
    SKILL = "skill"
    DECISION = "decision"
    EXECUTION = "execution"
    NOTE = "note"


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str = ""
    type: str = ""
    content: str = ""
    metadata: dict = field(default_factory=dict)
    source: str = ""
    tags: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    relevance: float = 0.0  # Set by search/retrieve

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
            "source": self.source,
            "tags": self.tags,
            "timestamp": self.timestamp,
            "relevance": self.relevance,
        }


@dataclass
class MemoryQuery:
    """Query parameters for memory retrieval."""
    type: Optional[str] = None
    text: str = ""
    tags: list[str] = field(default_factory=list)
    source: Optional[str] = None
    limit: int = 10
    min_relevance: float = 0.0
    since: Optional[float] = None  # timestamp
    until: Optional[float] = None  # timestamp


class MemoryProvider(ABC):
    """Abstract base for memory providers.

    Every provider must implement these methods.
    The rest of JARVIS only uses this interface.
    """

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> dict:
        """Store a memory entry."""
        ...

    @abstractmethod
    async def retrieve(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Retrieve memories matching query."""
        ...

    @abstractmethod
    async def search(self, text: str, limit: int = 10) -> list[MemoryEntry]:
        """Full-text search across all memories."""
        ...

    @abstractmethod
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID."""
        ...

    @abstractmethod
    async def delete(self, entry_id: str) -> dict:
        """Delete a memory by ID."""
        ...

    @abstractmethod
    async def count(self, type: Optional[str] = None) -> int:
        """Count memories, optionally filtered by type."""
        ...

    @abstractmethod
    async def list_types(self) -> dict[str, int]:
        """List all memory types and their counts."""
        ...


class SQLiteMemoryProvider(MemoryProvider):
    """SQLite-backed memory provider using FTS5 for search.

    Stores in the main jarvis.db database.
    Uses FTS5 for full-text search (fast, no embeddings needed).
    """

    def __init__(self):
        self._db = None

    async def _get_db(self):
        if self._db is None:
            from ..core.database import get_db
            self._db = await get_db()
        return self._db

    async def store(self, entry: MemoryEntry) -> dict:
        """Store a memory entry in the memories table."""
        db = await self._get_db()
        entry_id = entry.id or f"mem:{int(entry.timestamp * 1000)}"

        await db._db.execute(
            """INSERT OR REPLACE INTO memories
               (id, type, content, metadata, source, tags, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entry_id,
                entry.type,
                entry.content,
                json.dumps(entry.metadata),
                entry.source,
                json.dumps(entry.tags),
                entry.timestamp,
            ),
        )
        # v3.1: Sync to standalone FTS5 index
        await db._db.execute(
            "INSERT INTO memories_fts (type, content, source, tags) VALUES (?, ?, ?, ?)",
            (entry.type, entry.content, entry.source, json.dumps(entry.tags)),
        )
        await db._db.commit()
        return {"ok": True, "id": entry_id}

    async def retrieve(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Retrieve memories with optional filters."""
        db = await self._get_db()

        conditions = []
        params = []

        if query.type:
            conditions.append("type = ?")
            params.append(query.type)
        if query.source:
            conditions.append("source = ?")
            params.append(query.source)
        if query.since:
            conditions.append("timestamp >= ?")
            params.append(query.since)
        if query.until:
            conditions.append("timestamp <= ?")
            params.append(query.until)
        if query.tags:
            for tag in query.tags:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")

        where = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM memories WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(query.limit)

        cursor = await db._db.execute(sql, params)
        rows = await cursor.fetchall()

        entries = []
        for row in rows:
            entries.append(MemoryEntry(
                id=row[0],
                type=row[1],
                content=row[2],
                metadata=json.loads(row[3]) if row[3] else {},
                source=row[4] or "",
                tags=json.loads(row[5]) if row[5] else [],
                timestamp=row[6] or 0,
            ))

        return entries

    async def search(self, text: str, limit: int = 10) -> list[MemoryEntry]:
        """Full-text search using FTS5."""
        db = await self._get_db()

        try:
            cursor = await db._db.execute(
                """SELECT m.id, m.type, m.content, m.metadata, m.source, m.tags,
                          m.timestamp, snippet(memories_fts, 1, '<b>', '</b>', '...', 32) as snip,
                          rank
                   FROM memories_fts f
                   JOIN memories m ON m.type = f.type
                       AND m.content = f.content
                       AND m.source = f.source
                   WHERE memories_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (text, limit),
            )
            rows = await cursor.fetchall()

            entries = []
            for row in rows:
                entries.append(MemoryEntry(
                    id=row[0],
                    type=row[1],
                    content=row[2],
                    metadata=json.loads(row[3]) if row[3] else {},
                    source=row[4] or "",
                    tags=json.loads(row[5]) if row[5] else [],
                    timestamp=row[6] or 0,
                    relevance=abs(row[8]) if row[8] else 0,
                ))
            return entries
        except Exception:
            # Fallback to LIKE search if FTS5 table doesn't exist
            cursor = await db._db.execute(
                """SELECT id, type, content, metadata, source, tags, timestamp
                   FROM memories
                   WHERE content LIKE ?
                   ORDER BY timestamp DESC LIMIT ?""",
                (f"%{text}%", limit),
            )
            rows = await cursor.fetchall()
            return [
                MemoryEntry(
                    id=r[0], type=r[1], content=r[2],
                    metadata=json.loads(r[3]) if r[3] else {},
                    source=r[4] or "", tags=json.loads(r[5]) if r[5] else [],
                    timestamp=r[6] or 0,
                )
                for r in rows
            ]

    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID."""
        db = await self._get_db()
        cursor = await db._db.execute(
            "SELECT * FROM memories WHERE id = ?", (entry_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return MemoryEntry(
            id=row[0], type=row[1], content=row[2],
            metadata=json.loads(row[3]) if row[3] else {},
            source=row[4] or "", tags=json.loads(row[5]) if row[5] else [],
            timestamp=row[6] or 0,
        )

    async def delete(self, entry_id: str) -> dict:
        """Delete a memory by ID."""
        db = await self._get_db()
        await db._db.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
        await db._db.execute("INSERT INTO memories_fts(memories_fts) VALUES('rebuild')")
        await db._db.commit()
        return {"ok": True}

    async def count(self, type: Optional[str] = None) -> int:
        """Count memories."""
        db = await self._get_db()
        if type:
            cursor = await db._db.execute(
                "SELECT COUNT(*) FROM memories WHERE type = ?", (type,)
            )
        else:
            cursor = await db._db.execute("SELECT COUNT(*) FROM memories")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def list_types(self) -> dict[str, int]:
        """List all memory types and their counts."""
        db = await self._get_db()
        cursor = await db._db.execute(
            "SELECT type, COUNT(*) FROM memories GROUP BY type"
        )
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}


# Memory provider registry — swap providers without changing callers
_providers: dict[str, type[MemoryProvider]] = {
    "sqlite": SQLiteMemoryProvider,
}
_active_provider_name = "sqlite"
_memory_instance: Optional[MemoryProvider] = None


def register_provider(name: str, provider_class: type[MemoryProvider]) -> None:
    """Register a new memory provider class."""
    _providers[name] = provider_class
    log.info(f"Registered memory provider: {name}")


def set_provider(name: str) -> None:
    """Set the active memory provider by name."""
    global _active_provider_name, _memory_instance
    if name not in _providers:
        raise ValueError(f"Unknown provider: {name}. Available: {list(_providers.keys())}")
    _active_provider_name = name
    _memory_instance = None  # Force re-creation
    log.info(f"Memory provider set to: {name}")


def get_memory() -> MemoryProvider:
    """Get the active memory provider (singleton)."""
    global _memory_instance
    if _memory_instance is None:
        if _active_provider_name not in _providers:
            raise ValueError(f"Provider '{_active_provider_name}' not registered")
        _memory_instance = _providers[_active_provider_name]()
    return _memory_instance


# Convenience alias
memory = get_memory()
