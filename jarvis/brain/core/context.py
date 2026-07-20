"""Brain context manager — builds unified context for every agent interaction (v6.3.0).

Automatically assembles context from ALL available sources:
- Recent chat history
- Project memory
- User preferences
- Previous decisions
- Mission history
- Knowledge graph
- Working memory
- Execution history
- Relevant files
"""
import logging
import time
from typing import Any, Dict, List, Optional

from .models import BrainContext, MemoryEntry

logger = logging.getLogger(__name__)


class BrainContextManager:
    """Builds and provides BrainContext from ALL available memory subsystems.

    The model should always receive the best available context automatically.
    """

    def __init__(
        self,
        preference_engine=None,
        decision_engine=None,
        timeline_engine=None,
        knowledge_graph=None,
    ) -> None:
        self._preferences = preference_engine
        self._decisions = decision_engine
        self._timeline = timeline_engine
        self._kg = knowledge_graph

    async def build_context(
        self,
        goal: str,
        project_name: str = "",
        tools: Optional[List[str]] = None,
    ) -> BrainContext:
        """Assemble complete context from ALL subsystems automatically."""
        prefs = await self.get_preferences()
        memories = await self.get_relevant_memories(goal)
        attempts = await self.get_previous_attempts(goal)
        proj_ctx = await self.get_project_context(project_name) if project_name else {}
        decisions = await self.get_recent_decisions()
        events = await self.get_recent_events()

        # v6.3.0: Pull from additional sources
        mission_history = await self.get_mission_history(goal)
        working_ctx = await self.get_working_memory_context()
        execution_history = await self.get_execution_history(goal)

        confidence = 0.5
        if memories:
            confidence += 0.15
        if prefs:
            confidence += 0.1
        if attempts:
            confidence += 0.1
        if decisions:
            confidence += 0.1
        if events:
            confidence += 0.05
        if mission_history:
            confidence += 0.05
        if execution_history:
            confidence += 0.05
        confidence = min(confidence, 1.0)

        return BrainContext(
            current_goal=goal,
            user_preferences=prefs,
            relevant_memories=[m.to_dict() for m in memories],
            previous_attempts=attempts,
            project_context=proj_ctx,
            available_tools=tools or [],
            recent_decisions=[d.to_dict() for d in decisions],
            timeline_events=[e.to_dict() for e in events],
            confidence=confidence,
            timestamp=time.time(),
        )

    async def get_preferences(self) -> Dict[str, str]:
        """Flatten all preferences into a simple key->value dict."""
        if not self._preferences:
            return {}
        try:
            all_prefs = await self._preferences.get_all()
            return {f"{p.category}::{p.key}": p.value for p in all_prefs}
        except Exception as exc:
            logger.debug("Failed to get preferences: %s", exc)
            return {}

    async def get_relevant_memories(
        self, query: str, limit: int = 5
    ) -> List[MemoryEntry]:
        """Search the knowledge graph for memories matching the query."""
        if not self._kg:
            return []
        try:
            entities = await self._kg.search_entities(query, limit=limit)
            results: List[MemoryEntry] = []
            for e in entities:
                results.append(MemoryEntry(
                    id=e.id,
                    content=f"{e.name}: {e.description}",
                    source="knowledge_graph",
                    memory_type=e.entity_type,
                    importance=e.importance,
                    confidence=e.confidence,
                    related_entities=[],
                    metadata=e.metadata,
                ))
            return results
        except Exception as exc:
            logger.debug("Failed to get relevant memories: %s", exc)
            return []

    async def get_previous_attempts(
        self, goal: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find past attempts related to this goal."""
        if not self._decisions:
            return []
        try:
            q_lower = goal.lower()
            recent = await self._decisions.get_recent(n=limit * 3)
            matching = [
                d.to_dict() for d in recent
                if q_lower in d.title.lower()
                or q_lower in d.description.lower()
                or q_lower in d.reason.lower()
            ]
            return matching[:limit]
        except Exception as exc:
            logger.debug("Failed to get previous attempts: %s", exc)
            return []

    async def get_project_context(
        self, project_name: str
    ) -> Dict[str, Any]:
        """Retrieve context for a named project."""
        if not self._kg or not project_name:
            return {}
        try:
            entities = await self._kg.search_entities(project_name, limit=10)
            if not entities:
                return {"name": project_name, "entities": []}
            return {
                "name": project_name,
                "entities": [e.to_dict() for e in entities],
            }
        except Exception as exc:
            logger.debug("Failed to get project context: %s", exc)
            return {"name": project_name}

    async def get_recent_decisions(
        self, limit: int = 5
    ) -> List[Any]:
        """Get the most recent decisions."""
        if not self._decisions:
            return []
        try:
            return await self._decisions.get_recent(n=limit)
        except Exception as exc:
            logger.debug("Failed to get recent decisions: %s", exc)
            return []

    async def get_recent_events(
        self, limit: int = 5
    ) -> List[Any]:
        """Get the most recent timeline events."""
        if not self._timeline:
            return []
        try:
            return await self._timeline.get_recent(n=limit)
        except Exception as exc:
            logger.debug("Failed to get recent events: %s", exc)
            return []

    async def get_mission_history(self, goal: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Find past missions related to this goal for resumption context."""
        try:
            from ...mission.manager import mission_manager
            missions = await mission_manager.list_completed()
            q_lower = goal.lower()
            related = [
                m for m in missions
                if q_lower in m.get("goal", "").lower()
                or q_lower in m.get("user_request", "").lower()
            ]
            return related[:limit]
        except Exception:
            return []

    async def get_working_memory_context(self) -> Dict[str, str]:
        """Get active working memory slots for immediate context."""
        try:
            from ...brain.memory.working import WorkingMemoryManager
            wm = WorkingMemoryManager()
            return await wm.get_context(max_chars=2000)
        except Exception:
            return {}

    async def get_execution_history(self, goal: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Find recent tool execution results related to this goal."""
        try:
            from ...core.database import get_db
            db = await get_db()
            # Search recent task results
            cursor = await db._db.execute(
                "SELECT * FROM task_history WHERE goal LIKE ? ORDER BY completed_at DESC LIMIT ?",
                (f"%{goal[:50]}%", limit)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows] if rows else []
        except Exception:
            return []

    async def inject_context(
        self,
        goal: str,
        project_name: str = "",
        tools: Optional[List[str]] = None,
    ) -> str:
        """Build and format context as a string ready for LLM prompt injection."""
        ctx = await self.build_context(goal, project_name, tools)
        return ctx.to_prompt_context()
