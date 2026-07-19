"""Living Dashboard manager — aggregates subsystem data for the WebSocket UI."""

import os
import time
from typing import Any, Dict, List, Optional


class LivingDashboardManager:
    """Aggregates data from JARVIS subsystems into a single dashboard payload.

    All ``get_*`` methods return plain dicts so they can be serialised
    directly to JSON for the WebSocket layer.  When a subsystem is not
    available the corresponding section falls back to empty data.
    """

    def __init__(self) -> None:
        self._start_time: float = time.time()
        self._current_project: str = ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _elapsed(self) -> float:
        return round(time.time() - self._start_time, 2)

    def _now_iso(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    async def _try_brain_thoughts(self) -> List[Dict[str, Any]]:
        try:
            from jarvis.brain import LivingBrain
            brain = LivingBrain()
            raw = await brain.get_recent_thoughts(limit=10)
            return [
                {
                    "timestamp": getattr(t, "timestamp", self._now_iso()),
                    "content": getattr(t, "content", str(t)),
                    "category": getattr(t, "category", "general"),
                    "confidence": getattr(t, "confidence", 0.5),
                    "actions_proposed": getattr(t, "actions_proposed", []),
                }
                for t in raw
            ]
        except Exception:
            return []

    async def _try_missions(self) -> List[Dict[str, Any]]:
        try:
            from jarvis.mission import MissionManager
            mgr = MissionManager()
            missions = await mgr.list_active()
            return [
                {
                    "id": getattr(m, "id", ""),
                    "name": getattr(m, "name", "unnamed"),
                    "status": getattr(m, "status", "unknown"),
                    "progress": getattr(m, "progress", 0),
                }
                for m in missions
            ]
        except Exception:
            return []

    async def _try_workers(self) -> List[Dict[str, Any]]:
        try:
            from jarvis.agents import AgentRegistry
            reg = AgentRegistry()
            agents = reg.list_active()
            return [
                {
                    "name": getattr(a, "name", "unknown"),
                    "role": getattr(a, "role", "agent"),
                    "current_task": getattr(a, "current_task", "none"),
                    "confidence": getattr(a, "confidence", 0.0),
                    "status": getattr(a, "status", "idle"),
                    "last_active": getattr(a, "last_active", self._now_iso()),
                }
                for a in agents
            ]
        except Exception:
            return []

    async def _try_memories(self, limit: int) -> List[Dict[str, Any]]:
        try:
            from jarvis.memory import MemoryStore
            store = MemoryStore()
            entries = await store.recent(limit=limit)
            return [
                {
                    "id": getattr(e, "id", ""),
                    "content": getattr(e, "content", str(e)),
                    "timestamp": getattr(e, "timestamp", self._now_iso()),
                    "category": getattr(e, "category", "general"),
                }
                for e in entries
            ]
        except Exception:
            return []

    async def _try_suggestions(self) -> List[Dict[str, Any]]:
        try:
            from jarvis.suggestions import SuggestionEngine
            engine = SuggestionEngine()
            suggestions = await engine.get_active()
            return [
                {
                    "id": getattr(s, "id", ""),
                    "title": getattr(s, "title", ""),
                    "description": getattr(s, "description", ""),
                    "priority": getattr(s, "priority", "low"),
                }
                for s in suggestions
            ]
        except Exception:
            return []

    def _system_metrics(self) -> Dict[str, Any]:
        metrics: Dict[str, Any] = {}
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            metrics["memory_mb"] = round(usage.ru_maxrss / 1024 / 1024, 2)
        except Exception:
            metrics["memory_mb"] = 0.0

        try:
            cpu_count = os.cpu_count() or 1
            metrics["cpu_count"] = cpu_count
        except Exception:
            metrics["cpu_count"] = 1

        metrics["uptime_seconds"] = self._elapsed()
        return metrics

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_status(self) -> Dict[str, Any]:
        """Return a full dashboard snapshot."""
        return await self.to_websocket_payload()

    async def get_mission_queue(self) -> List[Dict[str, Any]]:
        return await self._try_missions()

    async def get_thoughts(self) -> List[Dict[str, Any]]:
        return await self._try_brain_thoughts()

    async def get_workers_status(self) -> List[Dict[str, Any]]:
        return await self._try_workers()

    async def get_recent_memories(self, limit: int = 10) -> List[Dict[str, Any]]:
        return await self._try_memories(limit)

    async def get_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Return timeline events from the last *hours* hours."""
        try:
            from jarvis.journal import Journal
            journal = Journal()
            cutoff = time.time() - (hours * 3600)
            events = await journal.events_since(cutoff)
            return [
                {
                    "timestamp": getattr(e, "timestamp", self._now_iso()),
                    "title": getattr(e, "title", ""),
                    "description": getattr(e, "description", ""),
                    "category": getattr(e, "category", "general"),
                }
                for e in events
            ]
        except Exception:
            return []

    async def get_suggestions(self) -> List[Dict[str, Any]]:
        return await self._try_suggestions()

    async def get_system_metrics(self) -> Dict[str, Any]:
        return self._system_metrics()

    async def to_websocket_payload(self) -> Dict[str, Any]:
        """Build the complete payload consumed by the WebSocket dashboard."""
        thoughts = await self._try_brain_thoughts()
        missions = await self._try_missions()
        workers = await self._try_workers()
        memories = await self._try_memories(10)
        suggestions = await self._try_suggestions()
        timeline = await self.get_timeline(24)
        metrics = self._system_metrics()

        return {
            "timestamp": self._now_iso(),
            "neural_core_status": "online" if thoughts else "standby",
            "mission_queue": missions,
            "thoughts": thoughts,
            "workers": workers,
            "recent_memories": memories,
            "timeline": timeline,
            "suggestions": suggestions,
            "current_project": self._current_project,
            "system_metrics": metrics,
            "uptime": self._elapsed(),
        }
