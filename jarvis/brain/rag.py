"""RAG Memory — Retrieval-Augmented Generation with context assembly.

Assembles relevant context from multiple memory sources (conversations,
knowledge graph, skills, task history) to augment LLM calls. Uses keyword
scoring since we avoid torch/numpy on Python 3.9.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class ContextChunk:
    """A piece of retrieved context."""
    source: str  # which system it came from
    content: str
    relevance: float  # 0-1
    metadata: dict = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "content": self.content[:200],
            "relevance": round(self.relevance, 3),
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class RAGQuery:
    """A retrieval query with optional filters."""
    text: str
    max_chunks: int = 10
    min_relevance: float = 0.1
    sources: list[str] = field(default_factory=list)  # empty = all
    time_decay: bool = True  # prefer recent context


class RAGMemory:
    """Retrieval-augmented memory that assembles context from all sources."""

    # Source weights (how much to trust each source)
    SOURCE_WEIGHTS = {
        "conversation": 0.8,
        "knowledge_graph": 0.9,
        "skill": 0.7,
        "task_history": 0.6,
        "memory_store": 0.75,
        "project": 0.85,
    }

    def __init__(self):
        self._retrieval_count = 0
        self._total_relevance = 0.0

    def _tokenize(self, text: str) -> set[str]:
        """Simple tokenization for keyword matching."""
        return set(re.findall(r'\w{2,}', text.lower()))

    def _score(self, query_tokens: set[str], content: str, source: str) -> float:
        """Score content relevance to query using keyword overlap + source weight."""
        content_tokens = self._tokenize(content)
        if not query_tokens or not content_tokens:
            return 0.0

        overlap = len(query_tokens & content_tokens)
        # TF component: fraction of query tokens found
        tf = overlap / len(query_tokens) if query_tokens else 0
        # IDF-like: penalize very common words (simple version)
        source_weight = self.SOURCE_WEIGHTS.get(source, 0.5)

        return tf * source_weight

    async def retrieve(
        self,
        query: RAGQuery,
        db=None,
        knowledge_graph=None,
        skill_manager=None,
        project_memory=None,
    ) -> list[ContextChunk]:
        """Retrieve relevant context from all available sources."""
        query_tokens = self._tokenize(query.text)
        chunks: list[ContextChunk] = []
        sources_filter = set(query.sources) if query.sources else None

        # 1. Conversation history (from FTS5)
        if db and (not sources_filter or "conversation" in sources_filter):
            try:
                cursor = await db._db.execute(
                    """SELECT content, timestamp FROM conversations
                       WHERE content MATCH ? ORDER BY timestamp DESC LIMIT ?""",
                    (query.text, query.max_chunks),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    score = self._score(query_tokens, row[0], "conversation")
                    if score >= query.min_relevance:
                        chunks.append(ContextChunk(
                            source="conversation",
                            content=row[0],
                            relevance=score,
                            timestamp=row[1] or 0,
                        ))
            except Exception:
                pass

        # 2. Knowledge graph
        if knowledge_graph and (not sources_filter or "knowledge_graph" in sources_filter):
            try:
                result = await knowledge_graph.search_nodes(query.text, limit=query.max_chunks)
                for node in result.get("results", []):
                    content = f"{node['label']}: {node.get('content', '')}"
                    score = self._score(query_tokens, content, "knowledge_graph")
                    if score >= query.min_relevance:
                        chunks.append(ContextChunk(
                            source="knowledge_graph",
                            content=content,
                            relevance=score,
                            metadata={"node_id": node["id"], "node_type": node["type"]},
                        ))
            except Exception:
                pass

        # 3. Skills
        if skill_manager and (not sources_filter or "skill" in sources_filter):
            try:
                result = await skill_manager.find_similar(query.text)
                for match in result.get("matches", [])[:query.max_chunks]:
                    content = f"Skill: {match['name']} — {match['description']}"
                    score = self._score(query_tokens, content, "skill") * match.get("success_rate", 0.5)
                    if score >= query.min_relevance:
                        chunks.append(ContextChunk(
                            source="skill",
                            content=content,
                            relevance=score,
                            metadata={"skill_name": match["name"], "success_rate": match.get("success_rate", 0)},
                        ))
            except Exception:
                pass

        # 4. Task history
        if db and (not sources_filter or "task_history" in sources_filter):
            try:
                cursor = await db._db.execute(
                    """SELECT task_name, result, confidence, created_at FROM task_history
                       WHERE task_name LIKE ? OR result LIKE ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (f"%{query.text}%", f"%{query.text}%", query.max_chunks),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    content = f"Task: {row[0]} — {row[1][:200]}"
                    score = self._score(query_tokens, content, "task_history")
                    if score >= query.min_relevance:
                        chunks.append(ContextChunk(
                            source="task_history",
                            content=content,
                            relevance=score,
                            metadata={"confidence": row[2]},
                            timestamp=row[3] or 0,
                        ))
            except Exception:
                pass

        # 5. Memory store
        if db and (not sources_filter or "memory_store" in sources_filter):
            try:
                cursor = await db._db.execute(
                    """SELECT m.content, m.type, m.tags, m.timestamp FROM memories m
                       JOIN memories_fts f ON m.rowid = f.rowid
                       WHERE memories_fts MATCH ?
                       ORDER BY rank LIMIT ?""",
                    (query.text, query.max_chunks),
                )
                rows = await cursor.fetchall()
                for row in rows:
                    score = self._score(query_tokens, row[0], "memory_store")
                    if score >= query.min_relevance:
                        chunks.append(ContextChunk(
                            source="memory_store",
                            content=row[0],
                            relevance=score,
                            metadata={"type": row[1], "tags": row[2]},
                            timestamp=row[3] or 0,
                        ))
            except Exception:
                pass

        # Apply time decay if requested
        if query.time_decay:
            now = time.time()
            for chunk in chunks:
                if chunk.timestamp > 0:
                    age_hours = (now - chunk.timestamp) / 3600
                    decay = 1.0 / (1.0 + age_hours * 0.05)  # gentle decay
                    chunk.relevance *= decay

        # Sort by relevance and limit
        chunks.sort(key=lambda c: c.relevance, reverse=True)
        chunks = chunks[:query.max_chunks]

        # Stats
        self._retrieval_count += 1
        if chunks:
            self._total_relevance += sum(c.relevance for c in chunks) / len(chunks)

        logger.debug(f"RAG: retrieved {len(chunks)} chunks for '{query.text[:50]}'")
        return chunks

    def assemble_context(
        self,
        chunks: list[ContextChunk],
        max_tokens: int = 3000,
    ) -> str:
        """Assemble retrieved chunks into a context string for LLM."""
        if not chunks:
            return ""

        parts = ["## Relevant Context"]
        current_tokens = 0  # rough estimate: 1 token ≈ 4 chars

        for chunk in chunks:
            text = f"\n[{chunk.source}] {chunk.content}"
            est_tokens = len(text) // 4
            if current_tokens + est_tokens > max_tokens:
                break
            parts.append(text)
            current_tokens += est_tokens

        return "\n".join(parts)

    def get_stats(self) -> dict:
        avg_relevance = (
            self._total_relevance / self._retrieval_count
            if self._retrieval_count > 0 else 0
        )
        return {
            "total_retrievals": self._retrieval_count,
            "avg_relevance": round(avg_relevance, 3),
            "source_weights": self.SOURCE_WEIGHTS,
        }


# Module-level singleton
rag_memory = RAGMemory()
