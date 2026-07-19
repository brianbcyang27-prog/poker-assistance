"""JARVIS Living Dashboard — live status feed for the UI.

Provides a single async interface that aggregates data from every
subsystem and serialises it into a WebSocket-ready payload.
"""

from typing import Any, Dict, List, Optional

from jarvis.living_dashboard.manager import LivingDashboardManager
from jarvis.living_dashboard.models import (
    DashboardStatus,
    ThoughtEntry,
    WorkerStatus,
)

__all__ = [
    "LivingDashboard",
    "DashboardStatus",
    "ThoughtEntry",
    "WorkerStatus",
]


class LivingDashboard:
    """Public facade over :class:`LivingDashboardManager`.

    Methods are thin async wrappers so callers never depend on
    internal import paths.
    """

    def __init__(self) -> None:
        self._mgr = LivingDashboardManager()

    async def get_status(self) -> Dict[str, Any]:
        """Return the full dashboard data snapshot."""
        return await self._mgr.get_status()

    async def get_mission_queue(self) -> List[Dict[str, Any]]:
        """Return active missions."""
        return await self._mgr.get_mission_queue()

    async def get_thoughts(self) -> List[Dict[str, Any]]:
        """Return current brain thoughts and predictions."""
        return await self._mgr.get_thoughts()

    async def get_workers_status(self) -> List[Dict[str, Any]]:
        """Return status of all active workers."""
        return await self._mgr.get_workers_status()

    async def get_recent_memories(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent memories."""
        return await self._mgr.get_recent_memories(limit)

    async def get_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Return timeline events from the given window."""
        return await self._mgr.get_timeline(hours)

    async def get_suggestions(self) -> List[Dict[str, Any]]:
        """Return active suggestions."""
        return await self._mgr.get_suggestions()

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Return CPU, memory, and uptime metrics."""
        return await self._mgr.get_system_metrics()

    async def to_websocket_payload(self) -> Dict[str, Any]:
        """Build and return the complete WebSocket payload."""
        return await self._mgr.to_websocket_payload()
