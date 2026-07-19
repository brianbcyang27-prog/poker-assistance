"""Unified memory manager — single entry point for all memory operations."""
import logging
import time
from typing import Any, Dict, List, Optional

from .models import MemoryEntry

logger = logging.getLogger(__name__)


class MemoryManager:
    """Unifies all memory sources behind one interface."""

    def __init__(
        self,
        knowledge_graph=None,
        preference_engine=None,
        decision_engine=None,
        timeline_engine=None,
        consolidation_engine=None,
        knowledge_extractor=None,
    ) -> None:
        self._kg = knowledge_graph
        self._preferences = preference_engine
        self._decisions = decision_engine
        self._timeline = timeline_engine
        self._consolidation = consolidation_engine
        self._extractor = knowledge_extractor
        self._memories: Dict[str, MemoryEntry] = {}

    async def remember(
        self,
        content: str,
        memory_type: str = "fact",
        importance: str = "useful",
        source: str = "manual",
        related_entities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """Store a new memory across all relevant subsystems."""
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            importance=importance,
            source=source,
            related_entities=related_entities or [],
            metadata=metadata or {},
        )
        self._memories[entry.id] = entry

        if self._kg:
            try:
                from jarvis.knowledge.models import Entity, ImportanceLevel
                entity = Entity(
                    name=content[:100],
                    entity_type=memory_type,
                    description=content,
                    importance=importance,
                    confidence=entry.confidence,
                    metadata={"memory_id": entry.id, "source": source},
                )
                await self._kg.add_entity(entity)
            except Exception as exc:
                logger.debug("Failed to store in knowledge graph: %s", exc)

        logger.debug("Remembered: %s (type=%s, importance=%s)", content[:60], memory_type, importance)
        return entry

    async def recall(
        self,
        query: str,
        limit: int = 10,
        memory_type: str = "",
    ) -> List[MemoryEntry]:
        """Search all memory sources for relevant entries."""
        results: List[MemoryEntry] = []

        if self._kg:
            try:
                entities = await self._kg.search_entities(query, limit=limit)
                for e in entities:
                    if memory_type and e.entity_type != memory_type:
                        continue
                    results.append(MemoryEntry(
                        id=e.id,
                        content=f"{e.name}: {e.description}",
                        source="knowledge_graph",
                        memory_type=e.entity_type,
                        importance=e.importance,
                        confidence=e.confidence,
                        metadata=e.metadata,
                    ))
            except Exception as exc:
                logger.debug("Knowledge graph recall failed: %s", exc)

        q_lower = query.lower()
        for m in self._memories.values():
            if q_lower in m.content.lower():
                if memory_type and m.memory_type != memory_type:
                    continue
                if m.id not in {r.id for r in results}:
                    results.append(m)

        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:limit]

    async def forget(self, memory_id: str) -> bool:
        """Remove a memory by ID."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True

        if self._kg:
            try:
                result = await self._kg.delete_entity(memory_id)
                return result.get("ok", False)
            except Exception as exc:
                logger.debug("Failed to delete from knowledge graph: %s", exc)
        return False

    async def get_profile(self) -> Dict[str, Any]:
        """Build a user profile from preferences and memories."""
        profile: Dict[str, Any] = {
            "preferences": {},
            "facts": [],
            "lessons": [],
            "decisions_count": 0,
        }

        if self._preferences:
            try:
                all_prefs = await self._preferences.get_all()
                for p in all_prefs:
                    profile["preferences"][f"{p.category}::{p.key}"] = p.value
            except Exception as exc:
                logger.debug("Failed to get preferences for profile: %s", exc)

        for m in self._memories.values():
            if m.memory_type == "fact":
                profile["facts"].append(m.content[:200])
            elif m.memory_type == "lesson":
                profile["lessons"].append(m.content[:200])

        if self._decisions:
            try:
                active = await self._decisions.get_active()
                profile["decisions_count"] = len(active)
            except Exception as exc:
                logger.debug("Failed to count decisions: %s", exc)

        return profile

    async def get_context_string(self) -> str:
        """Build a formatted context string for LLM injection."""
        lines: List[str] = []

        profile = await self.get_profile()
        if profile["preferences"]:
            lines.append("User Preferences:")
            for k, v in list(profile["preferences"].items())[:8]:
                lines.append(f"  - {k}: {v}")

        if self._decisions:
            try:
                recent = await self._decisions.get_recent(n=3)
                if recent:
                    lines.append("Recent Decisions:")
                    for d in recent:
                        lines.append(f"  - {d.title}: {d.reason[:80]}")
            except Exception:
                pass

        if self._timeline:
            try:
                events = await self._timeline.get_recent(n=3)
                if events:
                    lines.append("Recent Events:")
                    for e in events:
                        lines.append(f"  - [{e.event_type}] {e.title}")
            except Exception:
                pass

        return "\n".join(lines) if lines else "No context available."

    async def consolidate(self) -> Dict[str, Any]:
        """Run memory consolidation across subsystems."""
        if not self._consolidation:
            return {"ok": False, "error": "No consolidation engine available"}
        try:
            result = await self._consolidation.consolidate()
            return {"ok": True, "result": result.to_dict()}
        except Exception as exc:
            logger.error("Consolidation failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    async def get_stats(self) -> Dict[str, Any]:
        """Return memory statistics from all subsystems."""
        stats: Dict[str, Any] = {
            "local_memories": len(self._memories),
            "kg_stats": {},
            "preferences_count": 0,
            "decisions_count": 0,
            "timeline_events": 0,
        }

        if self._kg:
            try:
                kg = await self._kg.get_stats()
                stats["kg_stats"] = {
                    "entities": kg.total_entities,
                    "relationships": kg.total_relationships,
                }
            except Exception:
                pass

        if self._preferences:
            try:
                prefs = await self._preferences.get_all()
                stats["preferences_count"] = len(prefs)
            except Exception:
                pass

        if self._decisions:
            try:
                decisions = await self._decisions.get_all()
                stats["decisions_count"] = len(decisions)
            except Exception:
                pass

        if self._timeline:
            try:
                summary = await self._timeline.get_summary()
                stats["timeline_events"] = summary.total_events
            except Exception:
                pass

        return stats

    async def export_all(self) -> Dict[str, Any]:
        """Full export of all memory subsystems."""
        export: Dict[str, Any] = {
            "memories": [m.to_dict() for m in self._memories.values()],
            "profile": await self.get_profile(),
            "stats": await self.get_stats(),
        }

        if self._kg:
            try:
                export["knowledge_graph"] = await self._kg.to_dict()
            except Exception:
                export["knowledge_graph"] = {}

        if self._decisions:
            try:
                all_d = await self._decisions.get_all()
                export["decisions"] = [d.to_dict() for d in all_d]
            except Exception:
                export["decisions"] = []

        if self._timeline:
            try:
                summary = await self._timeline.get_summary()
                export["timeline"] = summary.to_dict()
            except Exception:
                export["timeline"] = {}

        if self._preferences:
            try:
                all_p = await self._preferences.get_all()
                export["preferences"] = [p.to_dict() for p in all_p]
            except Exception:
                export["preferences"] = []

        return export
