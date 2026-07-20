"""Personal Memory — User profile, preferences, and relationship.

Stores long-term stable information about the user:
- Preferences (language, tools, workflows)
- Rules (never do X, always do Y)
- Context (projects, goals, style)
- Relationship (how long they've worked together, communication style)

Unlike episodic memory (what happened), personal memory is about WHO the user is.

Privacy rules:
- Never automatically save sensitive information
- Require confidence threshold for new memories
- Allow user editing and deletion
- Three modes: always_remember, ask_before, never_remember
"""

import time
import json
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger("jarvis.memory.personal")


class RememberMode(str, Enum):
    ALWAYS = "always"         # Always remember (preferences, tools)
    ASK = "ask"               # Ask before remembering (opinions, habits)
    NEVER = "never"           # Never store (sensitive info)


class MemoryCategory(str, Enum):
    PREFERENCE = "preference"     # What the user likes/dislikes
    TOOL = "tool"                 # Tools and software they use
    WORKFLOW = "workflow"         # How they work
    STYLE = "style"               # Communication and design preferences
    GOAL = "goal"                 # Current and future goals
    PROJECT = "project"           # Project context
    RULE = "rule"                 # Explicit rules (never do X)
    BIO = "bio"                   # Personal info (name, role)
    CONTEXT = "context"           # General context


@dataclass
class PersonalMemory:
    """A single personal memory — stable information about the user."""
    id: int = 0
    category: str = ""
    key: str = ""
    value: str = ""
    confidence: float = 0.8    # 0-1, how confident we are this is correct
    source: str = ""           # Where this memory came from
    remember_mode: str = "always"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "remember_mode": self.remember_mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class PersonalMemoryManager:
    """Manages personal memories about the user.

    Personal memories are the stable, long-term knowledge about who the user is,
    what they prefer, and how they work. These memories persist across sessions
    and form the basis of JARVIS's understanding of the user.

    Usage:
        pm = PersonalMemoryManager(db)

        # Remember a preference
        await pm.remember("preference", "language", "Python",
                         confidence=0.95, source="conversation")

        # Remember a rule
        await pm.remember("rule", "no_comments", "Brian prefers no comments in code",
                         confidence=1.0, source="explicit")

        # Search
        memories = await pm.search("Python")
        memories = await pm.get_by_category("preference")

        # Forget
        await pm.forget(memory_id=42)
    """

    # Confidence threshold: don't auto-store memories below this
    AUTO_STORE_THRESHOLD = 0.6

    def __init__(self, db=None):
        self._db = db
        self._initialized = False
        self._cache: list[PersonalMemory] = []

    async def _ensure_db(self):
        if self._initialized:
            return
        if self._db is None:
            from ...core.database import get_db
            self._db = await get_db()
        self._initialized = True
        await self._load_cache()

    async def _load_cache(self):
        """Load all personal memories into cache for fast access."""
        try:
            cursor = await self._db.execute(
                "SELECT id, category, key, value, confidence, source, remember_mode, created_at, updated_at "
                "FROM personal_memory ORDER BY category, key"
            )
            rows = await cursor.fetchall()
            self._cache = [self._row_to_memory(r) for r in rows]
        except Exception as e:
            log.warning(f"Failed to load personal memory cache: {e}")

    async def remember(
        self,
        category: str,
        key: str,
        value: str,
        confidence: float = 0.8,
        source: str = "",
        remember_mode: str = "always",
    ) -> dict:
        """Store a personal memory.

        Args:
            category: Memory category (preference, tool, workflow, etc.)
            key: Short identifier (e.g., "favorite_language", "ui_style")
            value: The memory content
            confidence: 0-1, how confident we are this is correct
            source: Where this came from (conversation, explicit, etc.)
            remember_mode: "always", "ask", or "never"

        Returns:
            {"ok": True, "id": memory_id, "mode": remember_mode}
        """
        await self._ensure_db()

        # Check confidence threshold
        if confidence < self.AUTO_STORE_THRESHOLD and remember_mode == "always":
            remember_mode = "ask"
            log.info(f"Low confidence ({confidence:.2f}), setting mode to 'ask'")

        now = time.time()

        cursor = await self._db.execute(
            """INSERT INTO personal_memory
               (category, key, value, confidence, source, remember_mode, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(category, key) DO UPDATE SET
               value = excluded.value,
               confidence = excluded.confidence,
               source = excluded.source,
               remember_mode = excluded.remember_mode,
               updated_at = excluded.updated_at""",
            (category, key, value, confidence, source, remember_mode, now, now),
        )
        await self._db.commit()
        memory_id = cursor.lastrowid

        # Update cache
        await self._load_cache()

        log.info(f"Remembered: {category}/{key} = {value[:50]} (confidence={confidence:.2f})")
        return {"ok": True, "id": memory_id, "mode": remember_mode}

    async def get(self, category: str, key: str) -> Optional[PersonalMemory]:
        """Get a specific personal memory."""
        await self._ensure_db()
        for m in self._cache:
            if m.category == category and m.key == key:
                return m
        return None

    async def get_by_category(self, category: str) -> list[PersonalMemory]:
        """Get all memories in a category."""
        await self._ensure_db()
        return [m for m in self._cache if m.category == category]

    async def search(self, query: str, limit: int = 20) -> list[PersonalMemory]:
        """Search personal memories by text."""
        await self._ensure_db()
        query_lower = query.lower()
        results = []
        for m in self._cache:
            if (query_lower in m.key.lower() or
                query_lower in m.value.lower() or
                query_lower in m.category.lower()):
                results.append(m)
        return results[:limit]

    async def get_all(self) -> list[PersonalMemory]:
        """Get all personal memories."""
        await self._ensure_db()
        return list(self._cache)

    async def get_profile(self) -> dict:
        """Get a user profile summary for LLM context.

        Returns a structured profile that can be injected into prompts.
        """
        await self._ensure_db()

        profile = {}
        for m in self._cache:
            if m.remember_mode == "never":
                continue
            if m.category not in profile:
                profile[m.category] = {}
            profile[m.category][m.key] = {
                "value": m.value,
                "confidence": m.confidence,
            }
        return profile

    async def get_context_string(self) -> str:
        """Get a human-readable profile string for LLM context injection."""
        await self._ensure_db()

        lines = []
        for m in self._cache:
            if m.remember_mode == "never":
                continue
            if m.confidence < 0.5:
                continue  # Skip low-confidence memories

            category_label = m.category.replace("_", " ").title()
            lines.append(f"[{category_label}] {m.key}: {m.value}")

        return "\n".join(lines) if lines else ""

    async def forget(self, memory_id: Optional[int] = None,
                     category: Optional[str] = None,
                     key: Optional[str] = None) -> dict:
        """Delete personal memories.

        Can delete by ID, or by category+key combination.
        """
        await self._ensure_db()

        if memory_id:
            await self._db.execute("DELETE FROM personal_memory WHERE id = ?", (memory_id,))
        elif category and key:
            await self._db.execute(
                "DELETE FROM personal_memory WHERE category = ? AND key = ?",
                (category, key),
            )
        else:
            return {"ok": False, "error": "Provide memory_id or category+key"}

        await self._db.commit()
        await self._load_cache()
        return {"ok": True}

    async def update_confidence(self, category: str, key: str, confidence: float) -> dict:
        """Update the confidence score for a memory."""
        await self._ensure_db()
        await self._db.execute(
            "UPDATE personal_memory SET confidence = ?, updated_at = ? WHERE category = ? AND key = ?",
            (confidence, time.time(), category, key),
        )
        await self._db.commit()
        await self._load_cache()
        return {"ok": True}

    async def count(self) -> int:
        """Count total personal memories."""
        return len(self._cache)

    def _row_to_memory(self, row) -> PersonalMemory:
        return PersonalMemory(
            id=row[0], category=row[1], key=row[2], value=row[3],
            confidence=row[4] or 0.8, source=row[5] or "",
            remember_mode=row[6] or "always",
            created_at=row[7] or 0, updated_at=row[8] or 0,
        )


# Module-level convenience
_personal: Optional[PersonalMemoryManager] = None


def get_personal_memory(db=None) -> PersonalMemoryManager:
    global _personal
    if _personal is None:
        _personal = PersonalMemoryManager(db)
    return _personal
