"""Episodic Memory — Experiences, decisions, and outcomes.

Humans don't remember every token. They remember experiences:
what happened, why it mattered, what was decided, and what the outcome was.

Episodes are automatically created from:
- Completed missions
- Important conversations
- User decisions
- Major code changes
- Project milestones

Each episode captures the essential context needed to recall an experience
without storing every raw message.
"""

import time
import json
import logging
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger("jarvis.memory.episodic")


class EpisodeType(str, Enum):
    CONVERSATION = "conversation"
    MISSION = "mission"
    DECISION = "decision"
    MILESTONE = "milestone"
    ERROR = "error"
    LEARNING = "learning"
    DAILY = "daily"


@dataclass
class Episode:
    """A single episodic memory — a compressed experience."""
    id: int = 0
    title: str = ""
    summary: str = ""
    episode_type: str = "conversation"
    project: str = ""
    participants: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    outcome: str = ""
    importance_score: float = 0.0
    tags: list[str] = field(default_factory=list)
    source_conversation_ids: list[str] = field(default_factory=list)
    source_task_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    consolidated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "episode_type": self.episode_type,
            "project": self.project,
            "participants": self.participants,
            "goals": self.goals,
            "decisions": self.decisions,
            "outcome": self.outcome,
            "importance_score": self.importance_score,
            "tags": self.tags,
            "created_at": self.created_at,
            "age_days": round((time.time() - self.created_at) / 86400, 1),
        }


class EpisodicMemoryManager:
    """Manages episodic memories — compressed experiences.

    Episodic memory captures what happened, why it mattered, and what was decided.
    Unlike raw conversation storage, episodes are pre-compressed summaries that
    can be efficiently retrieved and understood.

    Usage:
        em = EpisodicMemoryManager(db)

        # Create from mission completion
        await em.create_episode(
            title="JARVIS UI redesign discussion",
            episode_type="decision",
            summary="Redesigned JARVIS from pages to workspaces. Kept gold sphere.",
            decisions=["Keep 3D gold particle sphere", "Move to workspace-based UI"],
            outcome="Design approved, implementation started",
            importance_score=85,
        )

        # Retrieve relevant episodes
        episodes = await em.search("UI redesign")
        episodes = await em.get_by_project("JARVIS")
        episodes = await em.get_recent(limit=10)
    """

    def __init__(self, db=None):
        self._db = db
        self._initialized = False

    async def _ensure_db(self):
        if self._initialized:
            return
        if self._db is None:
            from ...core.database import get_db
            self._db = await get_db()
        self._initialized = True

    async def create_episode(
        self,
        title: str,
        summary: str,
        episode_type: str = "conversation",
        project: str = "",
        participants: Optional[list[str]] = None,
        goals: Optional[list[str]] = None,
        decisions: Optional[list[str]] = None,
        outcome: str = "",
        importance_score: float = 0.0,
        tags: Optional[list[str]] = None,
        source_conversation_ids: Optional[list[str]] = None,
        source_task_ids: Optional[list[str]] = None,
    ) -> dict:
        """Create a new episodic memory.

        Args:
            title: Short descriptive title
            summary: 1-3 sentence summary of what happened
            episode_type: Type of episode (conversation, mission, decision, milestone, etc.)
            project: Associated project name
            participants: Who was involved
            goals: What was being attempted
            decisions: What was decided
            outcome: What happened in the end
            importance_score: 0-100, how important this was
            tags: Categorical tags for filtering
            source_conversation_ids: Link to raw conversations
            source_task_ids: Link to task history
        """
        await self._ensure_db()

        now = time.time()
        if importance_score == 0:
            importance_score = self._auto_score(title, summary, decisions, outcome)

        cursor = await self._db.execute(
            """INSERT INTO episodes
               (title, summary, episode_type, project, participants, goals,
                decisions, outcome, importance_score, tags,
                source_conversation_ids, source_task_ids,
                created_at, consolidated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title, summary, episode_type, project,
                json.dumps(participants or []),
                json.dumps(goals or []),
                json.dumps(decisions or []),
                outcome, importance_score,
                json.dumps(tags or []),
                json.dumps(source_conversation_ids or []),
                json.dumps(source_task_ids or []),
                now, 0,
            ),
        )
        await self._db.commit()
        episode_id = cursor.lastrowid

        log.info(f"Created episode: {title} (importance={importance_score:.0f})")
        return {"ok": True, "id": episode_id, "importance": importance_score}

    async def get(self, episode_id: int) -> Optional[Episode]:
        """Get a specific episode by ID."""
        await self._ensure_db()
        cursor = await self._db.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_episode(row)

    async def search(self, query: str, limit: int = 10) -> list[Episode]:
        """Search episodes by text content."""
        await self._ensure_db()

        # Try FTS first, fall back to LIKE
        try:
            cursor = await self._db.execute(
                """SELECT * FROM episodes
                   WHERE title LIKE ? OR summary LIKE ? OR tags LIKE ?
                   ORDER BY importance_score DESC, created_at DESC
                   LIMIT ?""",
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            )
        except Exception:
            cursor = await self._db.execute(
                """SELECT * FROM episodes
                   WHERE title LIKE ? OR summary LIKE ?
                   ORDER BY importance_score DESC, created_at DESC
                   LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit),
            )
        rows = await cursor.fetchall()
        return [self._row_to_episode(r) for r in rows]

    async def get_recent(self, limit: int = 20) -> list[Episode]:
        """Get most recent episodes."""
        await self._ensure_db()
        cursor = await self._db.execute(
            "SELECT * FROM episodes ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_episode(r) for r in rows]

    async def get_by_project(self, project: str, limit: int = 20) -> list[Episode]:
        """Get episodes for a specific project."""
        await self._ensure_db()
        cursor = await self._db.execute(
            """SELECT * FROM episodes WHERE project = ?
               ORDER BY importance_score DESC, created_at DESC LIMIT ?""",
            (project, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_episode(r) for r in rows]

    async def get_important(self, min_importance: float = 50.0, limit: int = 20) -> list[Episode]:
        """Get high-importance episodes."""
        await self._ensure_db()
        cursor = await self._db.execute(
            """SELECT * FROM episodes WHERE importance_score >= ?
               ORDER BY importance_score DESC, created_at DESC LIMIT ?""",
            (min_importance, limit),
        )
        rows = await cursor.fetchall()
        return [self._row_to_episode(r) for r in rows]

    async def get_decisions(self, limit: int = 20) -> list[Episode]:
        """Get episodes that contain decisions."""
        await self._ensure_db()
        cursor = await self._db.execute(
            """SELECT * FROM episodes WHERE episode_type = 'decision'
               OR decisions != '[]'
               ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_episode(r) for r in rows]

    async def update_episode(self, episode_id: int, **kwargs) -> dict:
        """Update specific fields of an episode."""
        await self._ensure_db()
        allowed = {
            "title", "summary", "outcome", "importance_score",
            "tags", "decisions", "goals", "participants",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return {"ok": False, "error": "No valid fields to update"}

        set_clauses = []
        params = []
        for key, value in updates.items():
            if isinstance(value, list):
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            params.append(value)
        params.append(episode_id)

        await self._db.execute(
            f"UPDATE episodes SET {', '.join(set_clauses)} WHERE id = ?",
            params,
        )
        await self._db.commit()
        return {"ok": True, "updated": list(updates.keys())}

    async def delete_episode(self, episode_id: int) -> dict:
        """Delete an episode."""
        await self._ensure_db()
        await self._db.execute("DELETE FROM episodes WHERE id = ?", (episode_id,))
        await self._db.commit()
        return {"ok": True}

    async def count(self) -> int:
        """Count total episodes."""
        await self._ensure_db()
        cursor = await self._db.execute("SELECT COUNT(*) FROM episodes")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_stats(self) -> dict:
        """Get episode statistics."""
        await self._ensure_db()
        total = await self.count()

        cursor = await self._db.execute(
            "SELECT episode_type, COUNT(*) FROM episodes GROUP BY episode_type"
        )
        types = {row[0]: row[1] for row in await cursor.fetchall()}

        cursor = await self._db.execute(
            "SELECT AVG(importance_score) FROM episodes"
        )
        avg_importance = (await cursor.fetchone())[0] or 0

        cursor = await self._db.execute(
            "SELECT project, COUNT(*) FROM episodes WHERE project != '' GROUP BY project"
        )
        projects = {row[0]: row[1] for row in await cursor.fetchall()}

        return {
            "total": total,
            "by_type": types,
            "by_project": projects,
            "avg_importance": round(avg_importance, 1),
        }

    async def get_timeline(self, days: int = 30) -> list[dict]:
        """Get a timeline of episodes for visualization."""
        await self._ensure_db()
        since = time.time() - (days * 86400)
        cursor = await self._db.execute(
            """SELECT id, title, summary, episode_type, project,
                      importance_score, created_at
               FROM episodes WHERE created_at >= ?
               ORDER BY created_at DESC""",
            (since,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0], "title": r[1], "summary": r[2],
                "type": r[3], "project": r[4],
                "importance": r[5], "date": r[6],
            }
            for r in rows
        ]

    def _row_to_episode(self, row) -> Episode:
        return Episode(
            id=row[0], title=row[1], summary=row[2],
            episode_type=row[3], project=row[4],
            participants=json.loads(row[5]) if row[5] else [],
            goals=json.loads(row[6]) if row[6] else [],
            decisions=json.loads(row[7]) if row[7] else [],
            outcome=row[8] or "",
            importance_score=row[9] or 0,
            tags=json.loads(row[10]) if row[10] else [],
            source_conversation_ids=json.loads(row[11]) if row[11] else [],
            source_task_ids=json.loads(row[12]) if row[12] else [],
            created_at=row[13] or 0,
            consolidated_at=row[14] or 0,
        )

    def _auto_score(
        self,
        title: str,
        summary: str,
        decisions: Optional[list[str]],
        outcome: str,
    ) -> float:
        """Auto-compute importance score based on content signals."""
        score = 30.0  # baseline

        # Decisions are important
        if decisions:
            score += len(decisions) * 15

        # Outcomes matter
        if outcome:
            score += 10

        # Important keywords
        important = ["architecture", "decision", "critical", "bug", "launch",
                     "deploy", "milestone", "breakthrough", "completed"]
        text = (title + " " + summary).lower()
        for kw in important:
            if kw in text:
                score += 8

        return min(100.0, score)


# Module-level convenience
_episodic: Optional[EpisodicMemoryManager] = None


def get_episodic_memory(db=None) -> EpisodicMemoryManager:
    global _episodic
    if _episodic is None:
        _episodic = EpisodicMemoryManager(db)
    return _episodic
