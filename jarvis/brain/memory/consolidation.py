"""Memory Consolidator — Background compression of raw memories into episodes.

Similar to how humans consolidate memories during sleep, this process:
1. Collects raw conversations and task history
2. Identifies significant patterns and decisions
3. Compresses them into episodic memories
4. Updates personal memories from patterns
5. Cleans up low-value raw data

Run periodically or after significant events.
"""

import time
import json
import logging
from typing import Optional

log = logging.getLogger("jarvis.memory.consolidation")


class MemoryConsolidator:
    """Consolidates raw memories into structured episodic and personal memories.

    The consolidator runs as a background process that:
    - Scans recent conversations for significant content
    - Groups related conversations into episodes
    - Extracts personal preferences from user messages
    - Cleans up old, low-value raw data

    Usage:
        consolidator = MemoryConsolidator(db)
        result = await consolidator.consolidate()
        print(f"Created {result['episodes_created']} episodes")
    """

    # Minimum conversations to consolidate into an episode
    MIN_CONVERSATIONS_FOR_EPISODE = 2

    # Maximum age of conversations to consolidate (7 days)
    MAX_AGE_HOURS = 168

    def __init__(self, db=None):
        self._db = db
        self._initialized = False

    async def _ensure_db(self):
        if self._initialized:
            return
        if self._db is None:
            from ..core.database import get_db
            self._db = await get_db()
        self._initialized = True

    async def consolidate(self, force: bool = False) -> dict:
        """Run the full consolidation process.

        Args:
            force: If True, re-consolidate even recently consolidated data

        Returns:
            Summary of what was created/updated
        """
        await self._ensure_db()

        stats = {
            "episodes_created": 0,
            "personal_memories_extracted": 0,
            "conversations_archived": 0,
            "decisions_captured": 0,
        }

        # Step 1: Find unconsolidated conversations
        unconsolidated = await self._get_unconsolidated_conversations(force)
        log.info(f"Found {len(unconsolidated)} unconsolidated conversation sessions")

        # Step 2: Group by session and create episodes
        sessions = self._group_by_session(unconsolidated)
        for session_id, messages in sessions.items():
            if len(messages) < self.MIN_CONVERSATIONS_FOR_EPISODE:
                continue

            episode = await self._create_episode_from_conversation(session_id, messages)
            if episode:
                stats["episodes_created"] += 1
                stats["decisions_captured"] += len(episode.get("decisions", []))

        # Step 3: Extract personal memories from user messages
        personal_count = await self._extract_personal_memories(unconsolidated)
        stats["personal_memories_extracted"] = personal_count

        # Step 4: Extract decisions from task history
        decisions = await self._extract_decisions_from_tasks()
        stats["decisions_captured"] += decisions

        log.info(f"Consolidation complete: {stats}")
        return stats

    async def _get_unconsolidated_conversations(self, force: bool = False) -> list[dict]:
        """Get conversations that haven't been consolidated into episodes yet."""
        if force:
            since = time.time() - (self.MAX_AGE_HOURS * 3600)
            cursor = await self._db.execute(
                """SELECT session_id, role, content, timestamp
                   FROM conversations WHERE timestamp >= ?
                   ORDER BY session_id, timestamp""",
                (since,),
            )
        else:
            # Get conversations not linked to any episode
            cursor = await self._db.execute(
                """SELECT c.session_id, c.role, c.content, c.timestamp
                   FROM conversations c
                   WHERE c.timestamp >= ?
                     AND c.session_id NOT IN (
                       SELECT DISTINCT json_each.value
                       FROM episodes, json_each(episodes.source_conversation_ids)
                     )
                   ORDER BY c.session_id, c.timestamp""",
                (time.time() - (self.MAX_AGE_HOURS * 3600),),
            )
        rows = await cursor.fetchall()
        return [
            {"session_id": r[0], "role": r[1], "content": r[2], "timestamp": r[3]}
            for r in rows
        ]

    def _group_by_session(self, conversations: list[dict]) -> dict[str, list[dict]]:
        """Group conversations by session ID."""
        sessions: dict[str, list[dict]] = {}
        for conv in conversations:
            sid = conv["session_id"]
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(conv)
        return sessions

    async def _create_episode_from_conversation(
        self,
        session_id: str,
        messages: list[dict],
    ) -> Optional[dict]:
        """Create an episode from a group of related conversations."""
        if not messages:
            return None

        # Extract key information
        user_msgs = [m for m in messages if m["role"] == "user"]
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]

        if not user_msgs:
            return None

        # Build title from first user message
        first_msg = user_msgs[0]["content"]
        title = first_msg[:100].replace("\n", " ").strip()

        # Build summary
        all_content = " ".join(m["content"] for m in messages)

        # Extract decisions (look for decision-like patterns)
        decisions = self._extract_decisions(all_content)

        # Determine importance
        from .importance import importance_scorer
        score = importance_scorer.score(
            all_content,
            context={
                "type": "conversation",
                "has_decision": len(decisions) > 0,
            },
        )

        # Skip low-importance conversations
        if score < 30:
            return None

        # Create episode
        from .episodic import get_episodic_memory
        em = get_episodic_memory(self._db)

        result = await em.create_episode(
            title=title,
            summary=self._create_summary(messages),
            episode_type="conversation",
            participants=["Brian", "JARVIS"],
            decisions=decisions,
            importance_score=score,
            tags=self._extract_tags(all_content),
            source_conversation_ids=[session_id],
        )

        log.info(f"Created episode from session {session_id}: {title[:50]}...")
        return result

    def _create_summary(self, messages: list[dict]) -> str:
        """Create a brief summary of a conversation."""
        user_msgs = [m["content"][:200] for m in messages if m["role"] == "user"]
        assistant_msgs = [m["content"][:200] for m in messages if m["role"] == "assistant"]

        parts = []
        if user_msgs:
            parts.append(f"User discussed: {user_msgs[0]}")
        if len(messages) > 2:
            parts.append(f"Conversation had {len(messages)} messages")
        if assistant_msgs:
            last = assistant_msgs[-1]
            if len(last) > 50:
                parts.append(f"JARVIS concluded: {last[:100]}")

        return ". ".join(parts) if parts else "Brief conversation"

    def _extract_decisions(self, text: str) -> list[str]:
        """Extract decision-like statements from text."""
        decisions = []
        text_lower = text.lower()

        # Pattern: "we decided to..."
        patterns = [
            r"decided to (\w[\w\s]{10,80})",
            r"going to (\w[\w\s]{10,80})",
            r"will use (\w[\w\s]{5,60})",
            r"chosen (\w[\w\s]{5,60})",
            r"the plan is to (\w[\w\s]{10,80})",
        ]

        for pattern in patterns:
            matches = __import__("re").findall(pattern, text_lower)
            for match in matches[:3]:  # limit per pattern
                decision = match.strip().rstrip(".")
                if len(decision) > 10:
                    decisions.append(decision.capitalize())

        return decisions[:5]  # max 5 decisions per conversation

    def _extract_tags(self, text: str) -> list[str]:
        """Extract topic tags from text."""
        tag_keywords = {
            "ui": "UI", "design": "design", "frontend": "frontend",
            "backend": "backend", "api": "API", "database": "database",
            "bug": "bug", "fix": "fix", "test": "testing",
            "deploy": "deployment", "memory": "memory", "ai": "AI",
            "voice": "voice", "pcb": "hardware", "cad": "hardware",
            "firmware": "firmware", "iot": "IoT",
        }

        text_lower = text.lower()
        tags = set()
        for keyword, tag in tag_keywords.items():
            if keyword in text_lower:
                tags.add(tag)
        return list(tags)[:5]

    async def _extract_personal_memories(self, conversations: list[dict]) -> int:
        """Extract personal preferences from user messages."""
        from .personal import get_personal_memory
        pm = get_personal_memory(self._db)

        count = 0
        for conv in conversations:
            if conv["role"] != "user":
                continue

            content = conv["content"].lower()

            # Preference patterns
            if "i prefer" in content or "i like" in content:
                key = self._extract_preference_key(conv["content"])
                if key:
                    await pm.remember(
                        "preference", key, conv["content"][:200],
                        confidence=0.7, source="conversation_extract",
                    )
                    count += 1

            # Rule patterns
            if "never" in content and ("do" in content or "use" in content):
                await pm.remember(
                    "rule", f"rule_{count}", conv["content"][:200],
                    confidence=0.75, source="conversation_extract",
                )
                count += 1

        return count

    def _extract_preference_key(self, text: str) -> Optional[str]:
        """Extract a preference key from user text."""
        text_lower = text.lower()
        if "language" in text_lower or "programming" in text_lower:
            return "programming_language"
        if "editor" in text_lower or "ide" in text_lower:
            return "editor"
        if "style" in text_lower or "ui" in text_lower:
            return "ui_style"
        if "framework" in text_lower:
            return "framework_preference"
        return None

    async def _extract_decisions_from_tasks(self) -> int:
        """Extract decisions from completed task history."""
        cursor = await self._db.execute(
            """SELECT plan_id, user_request, summary, created_at
               FROM task_history
               WHERE created_at >= ?
               ORDER BY created_at DESC LIMIT 50""",
            (time.time() - (self.MAX_AGE_HOURS * 3600),),
        )
        rows = await cursor.fetchall()

        count = 0
        for row in rows:
            if row[2]:  # has summary
                from .episodic import get_episodic_memory
                em = get_episodic_memory(self._db)

                # Check if already consolidated
                existing = await em.search(row[0], limit=1)
                if existing:
                    continue

                await em.create_episode(
                    title=f"Mission: {row[1][:80]}",
                    summary=row[2][:500],
                    episode_type="mission",
                    importance_score=50,
                    source_task_ids=[row[0]],
                )
                count += 1

        return count


# Module-level convenience
_consolidator: Optional[MemoryConsolidator] = None


def get_consolidator(db=None) -> MemoryConsolidator:
    global _consolidator
    if _consolidator is None:
        _consolidator = MemoryConsolidator(db)
    return _consolidator
