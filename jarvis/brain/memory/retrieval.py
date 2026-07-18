"""Memory Retrieval Engine — Intelligent context assembly.

When JARVIS receives a request, this engine:
1. Detects intent (what kind of memory is needed?)
2. Selects memory types to query
3. Retrieves relevant memories from all sources
4. Ranks by relevance + importance + recency
5. Compresses to fit context window
6. Returns assembled context for the LLM

This replaces the basic RAG with a smarter, multi-source retrieval system.
"""

import re
import time
import logging
from typing import Optional
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.memory.retrieval")


@dataclass
class RetrievalResult:
    """A single retrieved memory with metadata."""
    source: str          # which memory system
    content: str         # the memory content
    relevance: float     # 0-1, how relevant to the query
    importance: float    # 0-1, how important in general
    recency: float       # 0-1, how recent
    timestamp: float     # when it was created
    metadata: dict = field(default_factory=dict)

    @property
    def score(self) -> float:
        """Combined ranking score."""
        return (self.relevance * 0.5 +
                self.importance * 0.3 +
                self.recency * 0.2)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "content": self.content[:300],
            "relevance": round(self.relevance, 3),
            "importance": round(self.importance, 3),
            "recency": round(self.recency, 3),
            "score": round(self.score, 3),
            "metadata": self.metadata,
        }


class IntentDetector:
    """Detects what kind of memory the user needs."""

    INTENTS = {
        "recall": {
            "keywords": ["remember", "recall", "what did", "last time", "before",
                        "previously", "earlier", "ago", "history"],
            "memory_types": ["episodic", "conversation"],
        },
        "decision": {
            "keywords": ["decided", "decide", "decision", "chose", "agreed", "plan",
                        "why did", "reason", "rationale"],
            "memory_types": ["episodic", "decision"],
        },
        "project": {
            "keywords": ["project", "code", "codebase", "repository", "file",
                        "function", "class", "module", "architecture"],
            "memory_types": ["project", "knowledge_graph", "conversation"],
        },
        "preference": {
            "keywords": ["prefer", "like", "hate", "favorite", "style",
                        "always", "never", "rule", "preference"],
            "memory_types": ["personal", "preference"],
        },
        "continue": {
            "keywords": ["continue", "resume", "go on", "pick up", "where were",
                        "working on", "next step"],
            "memory_types": ["working", "episodic", "project"],
        },
        "learn": {
            "keywords": ["how does", "explain", "teach", "what is",
                        "why", "how to", "learn"],
            "memory_types": ["knowledge_graph", "episodic", "conversation"],
        },
    }

    def detect(self, query: str) -> list[str]:
        """Detect intent from a query. Returns list of matched intent types."""
        query_lower = query.lower()
        intents = []

        for intent, config in self.INTENTS.items():
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    intents.append(intent)
                    break

        # Default to general recall if no specific intent detected
        if not intents:
            intents = ["recall"]

        return intents

    def get_memory_types(self, intents: list[str]) -> list[str]:
        """Get which memory types to query based on detected intents."""
        types = set()
        for intent in intents:
            config = self.INTENTS.get(intent, {})
            types.update(config.get("memory_types", []))
        return list(types)


class MemoryRetrievalEngine:
    """Intelligent multi-source memory retrieval.

    Usage:
        engine = MemoryRetrievalEngine(db)
        result = await engine.retrieve("Continue the robot project")
        context = engine.assemble_context(result)
    """

    MAX_CONTEXT_CHARS = 4000

    def __init__(self, db=None):
        self._db = db
        self._intent_detector = IntentDetector()
        self._stats = {"retrievals": 0, "total_results": 0}

    async def retrieve(
        self,
        query: str,
        max_results: int = 15,
        memory_types: Optional[list[str]] = None,
    ) -> list[RetrievalResult]:
        """Retrieve relevant memories from all sources.

        Args:
            query: The user's query or context
            max_results: Maximum results to return
            memory_types: Override which memory types to query

        Returns:
            Ranked list of RetrievalResult
        """
        if self._db is None:
            from ..core.database import get_db
            self._db = await get_db()

        # 1. Detect intent
        intents = self._intent_detector.detect(query)
        if memory_types is None:
            memory_types = self._intent_detector.get_memory_types(intents)

        log.debug(f"Query: '{query[:50]}' | Intents: {intents} | Types: {memory_types}")

        results: list[RetrievalResult] = []

        # 2. Query each memory type
        if "working" in memory_types:
            results.extend(await self._query_working(query))

        if "personal" in memory_types or "preference" in memory_types:
            results.extend(await self._query_personal(query))

        if "episodic" in memory_types:
            results.extend(await self._query_episodes(query))

        if "conversation" in memory_types:
            results.extend(await self._query_conversations(query))

        if "knowledge_graph" in memory_types:
            results.extend(await self._query_graph(query))

        if "project" in memory_types:
            results.extend(await self._query_projects(query))

        if "decision" in memory_types:
            results.extend(await self._query_decisions(query))

        # 3. Rank by combined score
        results.sort(key=lambda r: r.score, reverse=True)

        # 4. Limit results
        results = results[:max_results]

        # Update stats
        self._stats["retrievals"] += 1
        self._stats["total_results"] += len(results)

        log.info(f"Retrieved {len(results)} memories for '{query[:50]}'")
        return results

    async def _query_working(self, query: str) -> list[RetrievalResult]:
        """Query working memory (current context)."""
        from .working import get_working_memory
        wm = get_working_memory(self._db)
        entries = await wm.get_all()

        results = []
        for slot, entry in entries.items():
            content = entry.get("content", "")
            relevance = self._keyword_score(query, content)
            if relevance > 0.1:
                results.append(RetrievalResult(
                    source="working_memory",
                    content=content,
                    relevance=relevance,
                    importance=entry.get("importance", 0.5),
                    recency=0.9,  # working memory is always recent
                    timestamp=entry.get("created_at", time.time()),
                    metadata={"slot": slot},
                ))
        return results

    async def _query_personal(self, query: str) -> list[RetrievalResult]:
        """Query personal memories (preferences, rules)."""
        from .personal import get_personal_memory
        pm = get_personal_memory(self._db)
        memories = await pm.search(query, limit=10)

        results = []
        for mem in memories:
            content = f"{mem.category}/{mem.key}: {mem.value}"
            relevance = self._keyword_score(query, content)
            if relevance > 0.1:
                results.append(RetrievalResult(
                    source="personal",
                    content=content,
                    relevance=relevance,
                    importance=mem.confidence,
                    recency=self._recency_score(mem.updated_at),
                    timestamp=mem.updated_at,
                    metadata={"category": mem.category, "key": mem.key},
                ))
        return results

    async def _query_episodes(self, query: str) -> list[RetrievalResult]:
        """Query episodic memories."""
        from .episodic import get_episodic_memory
        em = get_episodic_memory(self._db)
        episodes = await em.search(query, limit=10)

        results = []
        for ep in episodes:
            content = f"{ep.title}. {ep.summary}"
            if ep.decisions:
                content += f" Decisions: {'; '.join(ep.decisions)}"
            relevance = self._keyword_score(query, content)
            if relevance > 0.1:
                importance = ep.importance_score / 100.0
                results.append(RetrievalResult(
                    source="episodic",
                    content=content,
                    relevance=relevance,
                    importance=importance,
                    recency=self._recency_score(ep.created_at),
                    timestamp=ep.created_at,
                    metadata={"episode_id": ep.id, "type": ep.episode_type},
                ))
        return results

    async def _query_conversations(self, query: str) -> list[RetrievalResult]:
        """Query conversation history."""
        try:
            cursor = await self._db.execute(
                """SELECT content, timestamp FROM conversations
                   WHERE content LIKE ?
                   ORDER BY timestamp DESC LIMIT 10""",
                (f"%{query}%",),
            )
            rows = await cursor.fetchall()
        except Exception:
            return []

        results = []
        for row in rows:
            relevance = self._keyword_score(query, row[0])
            if relevance > 0.1:
                results.append(RetrievalResult(
                    source="conversation",
                    content=row[0],
                    relevance=relevance,
                    importance=0.3,
                    recency=self._recency_score(row[1]),
                    timestamp=row[1] or 0,
                ))
        return results

    async def _query_graph(self, query: str) -> list[RetrievalResult]:
        """Query knowledge graph."""
        try:
            from ..memory.graph import graph
            result = await graph.search_nodes(query, limit=10)
        except Exception:
            return []

        results = []
        for node in result.get("results", []):
            content = f"{node['label']}: {node.get('content', '')}"
            relevance = self._keyword_score(query, content)
            if relevance > 0.1:
                results.append(RetrievalResult(
                    source="knowledge_graph",
                    content=content,
                    relevance=relevance,
                    importance=0.5,
                    recency=0.5,
                    timestamp=node.get("created_at", 0),
                    metadata={"node_id": node["id"], "node_type": node["type"]},
                ))
        return results

    async def _query_projects(self, query: str) -> list[RetrievalResult]:
        """Query project memory."""
        try:
            cursor = await self._db.execute(
                "SELECT name, description, language, context FROM projects WHERE name LIKE ? OR description LIKE ?",
                (f"%{query}%", f"%{query}%"),
            )
            rows = await cursor.fetchall()
        except Exception:
            return []

        results = []
        for row in rows:
            content = f"Project: {row[0]}. {row[1] or ''}"
            relevance = self._keyword_score(query, content)
            if relevance > 0.1:
                results.append(RetrievalResult(
                    source="project",
                    content=content,
                    relevance=relevance,
                    importance=0.6,
                    recency=0.7,
                    timestamp=0,
                    metadata={"project_name": row[0], "language": row[2]},
                ))
        return results

    async def _query_decisions(self, query: str) -> list[RetrievalResult]:
        """Query decision history."""
        try:
            cursor = await self._db.execute(
                "SELECT topic, decision, reason, created_at FROM decisions WHERE topic LIKE ? OR decision LIKE ?",
                (f"%{query}%", f"%{query}%"),
            )
            rows = await cursor.fetchall()
        except Exception:
            return []

        results = []
        for row in rows:
            content = f"Decision: {row[0]} → {row[1]}"
            if row[2]:
                content += f" (Reason: {row[2]})"
            relevance = self._keyword_score(query, content)
            if relevance > 0.1:
                results.append(RetrievalResult(
                    source="decision",
                    content=content,
                    relevance=relevance,
                    importance=0.8,
                    recency=self._recency_score(row[3]),
                    timestamp=row[3] or 0,
                ))
        return results

    def assemble_context(
        self,
        results: list[RetrievalResult],
        max_chars: Optional[int] = None,
    ) -> str:
        """Assemble retrieved results into a context string for LLM injection."""
        max_chars = max_chars or self.MAX_CONTEXT_CHARS
        lines = []
        total = 0

        for r in results:
            text = f"[{r.source}] {r.content}"
            if total + len(text) > max_chars:
                remaining = max_chars - total
                if remaining > 80:
                    text = text[:remaining - 3] + "..."
                else:
                    break
            lines.append(text)
            total += len(text)

        return "\n".join(lines)

    def get_stats(self) -> dict:
        return dict(self._stats)

    def _keyword_score(self, query: str, content: str) -> float:
        """Simple keyword overlap scoring."""
        query_tokens = set(re.findall(r'\w{3,}', query.lower()))
        content_tokens = set(re.findall(r'\w{3,}', content.lower()))
        if not query_tokens:
            return 0.0
        overlap = len(query_tokens & content_tokens)
        return overlap / len(query_tokens)

    def _recency_score(self, timestamp: float) -> float:
        """Score recency: 1.0 for now, decays over time."""
        if timestamp <= 0:
            return 0.5
        age_hours = (time.time() - timestamp) / 3600
        return 1.0 / (1.0 + age_hours * 0.02)  # gentle decay


# Module-level singleton
retrieval_engine: Optional[MemoryRetrievalEngine] = None


def get_retrieval_engine(db=None) -> MemoryRetrievalEngine:
    global retrieval_engine
    if retrieval_engine is None:
        retrieval_engine = MemoryRetrievalEngine(db)
    return retrieval_engine
