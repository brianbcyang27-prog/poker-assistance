"""Working Memory — Short-term context manager.

Manages the current working context: active conversation, mission, project,
agents, files, and decisions. Automatically compresses and expires old context.

Think of this as JARVIS's "attention" — what it's currently focused on.
"""

import time
import json
import logging
from typing import Optional, Any
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.memory.working")

# Working memory slots — the key contexts JARVIS maintains
SLOTS = {
    "conversation": "Current conversation summary",
    "mission": "Active mission context",
    "project": "Current project being worked on",
    "agents": "Active agents and their tasks",
    "files": "Currently relevant files",
    "decisions": "Recent decisions made",
    "user_context": "What the user is trying to accomplish right now",
}

# Default expiration: 2 hours for most slots, longer for project/user_context
SLOT_EXPIRATION = {
    "conversation": 3600 * 1,       # 1 hour
    "mission": 3600 * 4,            # 4 hours
    "project": 3600 * 8,            # 8 hours
    "agents": 3600 * 2,             # 2 hours
    "files": 3600 * 2,              # 2 hours
    "decisions": 3600 * 4,          # 4 hours
    "user_context": 3600 * 8,       # 8 hours
}


@dataclass
class WorkingMemoryEntry:
    """A single working memory slot."""
    slot: str
    content: str
    priority: int = 5          # 1-10, higher = more important
    importance: float = 0.0    # computed importance
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0    # 0 = no expiration
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        if self.expires_at <= 0:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "slot": self.slot,
            "content": self.content,
            "priority": self.priority,
            "importance": self.importance,
            "age_minutes": round((time.time() - self.created_at) / 60, 1),
            "access_count": self.access_count,
            "expired": self.is_expired(),
        }


class WorkingMemoryManager:
    """Manages short-term working memory with automatic expiration and compression.

    Working memory is the "active context" — what JARVIS is currently focused on.
    Unlike long-term memory, working memory is ephemeral and self-maintaining.

    Usage:
        wm = WorkingMemoryManager(db)
        await wm.set("conversation", "Brian is working on JARVIS v4.1 memory system")
        await wm.set("project", "JARVIS - AI operating system")
        context = await wm.get_context()
    """

    MAX_TOTAL_CHARS = 4000  # Maximum total context characters
    COMPRESSION_THRESHOLD = 3000  # Start compressing when over this

    def __init__(self, db=None):
        self._db = db
        self._cache: dict[str, WorkingMemoryEntry] = {}
        self._initialized = False

    async def _ensure_db(self):
        if self._initialized:
            return
        if self._db is None:
            from ..core.database import get_db
            self._db = await get_db()
        self._initialized = True
        # Load existing working memory
        await self._load()

    async def _load(self):
        """Load working memory from database."""
        try:
            cursor = await self._db.execute(
                "SELECT slot, content, priority, importance, created_at, expires_at, access_count, last_accessed "
                "FROM working_memory"
            )
            rows = await cursor.fetchall()
            for row in rows:
                entry = WorkingMemoryEntry(
                    slot=row[0], content=row[1], priority=row[2],
                    importance=row[3], created_at=row[4], expires_at=row[5],
                    access_count=row[6], last_accessed=row[7],
                )
                if not entry.is_expired():
                    self._cache[entry.slot] = entry
                else:
                    # Clean up expired entries
                    await self._db.execute("DELETE FROM working_memory WHERE slot = ?", (entry.slot,))
            await self._db.commit()
        except Exception as e:
            log.warning(f"Failed to load working memory: {e}")

    async def set(self, slot: str, content: str, priority: int = 5, ttl: Optional[float] = None) -> dict:
        """Set a working memory slot.

        Args:
            slot: The memory slot name (e.g., 'conversation', 'mission')
            content: The content to remember
            priority: 1-10, higher = more important (affects compression order)
            ttl: Time to live in seconds. None = use slot default.
        """
        await self._ensure_db()

        if slot not in SLOTS:
            log.warning(f"Unknown working memory slot: {slot}")

        now = time.time()
        expiration = SLOT_EXPIRATION.get(slot, 3600 * 2)
        if ttl is not None:
            expiration = ttl

        entry = WorkingMemoryEntry(
            slot=slot,
            content=content,
            priority=priority,
            importance=self._compute_importance(content, priority),
            created_at=now,
            expires_at=now + expiration if expiration > 0 else 0,
            access_count=0,
            last_accessed=now,
        )

        self._cache[slot] = entry

        await self._db.execute(
            "INSERT OR REPLACE INTO working_memory "
            "(slot, content, priority, importance, created_at, expires_at, access_count, last_accessed) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (slot, content, priority, entry.importance, entry.created_at, entry.expires_at, 0, now),
        )
        await self._db.commit()

        log.debug(f"Working memory set: {slot} = {content[:80]}...")
        return {"ok": True, "slot": slot}

    async def get(self, slot: str) -> Optional[str]:
        """Get content from a working memory slot."""
        await self._ensure_db()

        entry = self._cache.get(slot)
        if entry is None:
            return None
        if entry.is_expired():
            del self._cache[slot]
            await self._db.execute("DELETE FROM working_memory WHERE slot = ?", (slot,))
            await self._db.commit()
            return None

        # Update access count
        entry.access_count += 1
        entry.last_accessed = time.time()
        await self._db.execute(
            "UPDATE working_memory SET access_count = access_count + 1, last_accessed = ? WHERE slot = ?",
            (entry.last_accessed, slot),
        )
        await self._db.commit()

        return entry.content

    async def get_all(self) -> dict[str, dict]:
        """Get all active working memory entries."""
        await self._ensure_db()
        self._cleanup_expired()
        return {slot: entry.to_dict() for slot, entry in self._cache.items()}

    async def get_context(self, max_chars: Optional[int] = None) -> str:
        """Get a compressed context string for LLM consumption.

        Returns a human-readable summary of the current working context,
        respecting character limits and prioritizing important information.
        """
        await self._ensure_db()
        self._cleanup_expired()

        max_chars = max_chars or self.MAX_TOTAL_CHARS
        lines = []
        total_chars = 0

        # Sort by priority (highest first), then by recency
        sorted_entries = sorted(
            self._cache.values(),
            key=lambda e: (-e.priority, -e.last_accessed),
        )

        for entry in sorted_entries:
            # Compress if over threshold
            content = entry.content
            if total_chars + len(content) > max_chars:
                # Try to fit a compressed version
                remaining = max_chars - total_chars
                if remaining > 100:
                    content = content[:remaining - 3] + "..."
                else:
                    break

            label = SLOTS.get(entry.slot, entry.slot).replace("Current ", "").replace("Active ", "")
            lines.append(f"[{label}] {content}")
            total_chars += len(content)

        return "\n".join(lines) if lines else "No active context."

    async def clear(self, slot: Optional[str] = None):
        """Clear a specific slot or all working memory."""
        await self._ensure_db()
        if slot:
            self._cache.pop(slot, None)
            await self._db.execute("DELETE FROM working_memory WHERE slot = ?", (slot,))
        else:
            self._cache.clear()
            await self._db.execute("DELETE FROM working_memory")
        await self._db.commit()

    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        expired = [s for s, e in self._cache.items() if e.is_expired()]
        for slot in expired:
            del self._cache[slot]

    def _compute_importance(self, content: str, priority: int) -> float:
        """Compute importance score for a working memory entry."""
        base = priority / 10.0

        # Boost importance for key signals
        important_keywords = [
            "decision", "important", "remember", "never forget",
            "architecture", "bug", "critical", "deadline", "goal",
        ]
        keyword_boost = sum(0.05 for kw in important_keywords if kw in content.lower())

        # Longer content is often more important
        length_boost = min(0.1, len(content) / 5000)

        return min(1.0, base + keyword_boost + length_boost)

    async def compress_conversation(self, messages: list[dict]) -> str:
        """Compress a list of conversation messages into a working memory summary.

        Instead of storing 100 messages, store a concise summary.
        """
        if not messages:
            return ""

        # Extract key signals
        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]

        # Build summary
        parts = []

        if user_msgs:
            last_user = user_msgs[-1].get("content", "")
            parts.append(f"User's latest: {last_user[:200]}")

        if len(user_msgs) > 1:
            parts.append(f"Conversation has {len(messages)} messages")

        # Extract topics from all messages
        all_content = " ".join(m.get("content", "") for m in messages)
        topics = self._extract_topics(all_content)
        if topics:
            parts.append(f"Topics: {', '.join(topics[:5])}")

        return ". ".join(parts)

    def _extract_topics(self, text: str) -> list[str]:
        """Extract key topics from text using simple keyword extraction."""
        import re
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())

        # Simple TF-based extraction
        word_freq: dict[str, int] = {}
        for w in words:
            if w not in {'this', 'that', 'with', 'from', 'have', 'been', 'were', 'they', 'their', 'what', 'when', 'where', 'which', 'about', 'would', 'could', 'should', 'there', 'more', 'also', 'some', 'very', 'just', 'into', 'only', 'other', 'than', 'then', 'them', 'these', 'those'}:
                word_freq[w] = word_freq.get(w, 0) + 1

        sorted_words = sorted(word_freq.items(), key=lambda x: -x[1])
        return [w for w, c in sorted_words[:8] if c >= 2]


# Module-level convenience
_working_memory: Optional[WorkingMemoryManager] = None


def get_working_memory(db=None) -> WorkingMemoryManager:
    global _working_memory
    if _working_memory is None:
        _working_memory = WorkingMemoryManager(db)
    return _working_memory
