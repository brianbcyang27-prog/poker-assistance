"""Worker Pool — Manages worker lifecycle and availability."""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

log = logging.getLogger("jarvis.pool")


class WorkerState(str, Enum):
    """Worker states."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class WorkerSlot:
    """A worker slot in the pool."""
    card_id: str           # e.g., "♥Q"
    name: str              # e.g., "Personal Assistant"
    suit: str              # e.g., "hearts"
    rank: str              # e.g., "Q"
    role: str              # e.g., "Personal"
    capabilities: List[str] = field(default_factory=list)
    state: str = WorkerState.IDLE
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_duration_ms: float = 0.0
    last_active: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "name": self.name,
            "suit": self.suit,
            "rank": self.rank,
            "role": self.role,
            "capabilities": self.capabilities,
            "state": self.state,
            "current_task": self.current_task,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }


class WorkerPool:
    """Manages the pool of available workers.

    The pool tracks:
        - Which workers are available
        - Which workers are busy
        - Worker capabilities and performance
        - Automatic load balancing
    """

    def __init__(self):
        self._workers: Dict[str, WorkerSlot] = {}
        self._handlers: Dict[str, Callable] = {}
        self._task_log: List[Dict[str, Any]] = []

    def register_worker(
        self,
        card_id: str,
        name: str,
        suit: str,
        rank: str,
        role: str,
        capabilities: Optional[List[str]] = None,
        handler: Optional[Callable] = None,
    ) -> WorkerSlot:
        """Register a worker in the pool."""
        worker = WorkerSlot(
            card_id=card_id,
            name=name,
            suit=suit,
            rank=rank,
            role=role,
            capabilities=capabilities or [],
        )
        self._workers[card_id] = worker

        if handler:
            self._handlers[card_id] = handler

        log.info(f"Registered worker: {card_id} ({name})")
        return worker

    def unregister_worker(self, card_id: str) -> bool:
        """Remove a worker from the pool."""
        if card_id in self._workers:
            del self._workers[card_id]
            self._handlers.pop(card_id, None)
            return True
        return False

    def get_worker(self, card_id: str) -> Optional[WorkerSlot]:
        """Get a worker by card ID."""
        return self._workers.get(card_id)

    def get_idle_workers(self) -> List[WorkerSlot]:
        """Get all idle workers."""
        return [w for w in self._workers.values() if w.state == WorkerState.IDLE]

    def get_busy_workers(self) -> List[WorkerSlot]:
        """Get all busy workers."""
        return [w for w in self._workers.values() if w.state == WorkerState.BUSY]

    def get_workers_by_capability(self, capability: str) -> List[WorkerSlot]:
        """Get workers with a specific capability."""
        return [
            w for w in self._workers.values()
            if capability in w.capabilities
        ]

    def get_best_worker(self, capability: Optional[str] = None) -> Optional[WorkerSlot]:
        """Get the best available worker for a task.

        Selection criteria:
            1. Must be idle
            2. Must have the required capability (if specified)
            3. Prefer worker with fewest tasks (load balancing)
            4. Prefer worker with lowest avg duration (performance)
        """
        candidates = self.get_idle_workers()

        if capability:
            candidates = [w for w in candidates if capability in w.capabilities]

        if not candidates:
            return None

        # Sort by load (fewest tasks) then by performance (lowest avg duration)
        candidates.sort(key=lambda w: (w.tasks_completed, w.avg_duration_ms))
        return candidates[0]

    async def assign_task(
        self,
        card_id: str,
        task_id: str,
        action: str,
        params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Assign a task to a specific worker.

        Returns:
            Result dict or None if worker unavailable
        """
        worker = self._workers.get(card_id)
        if not worker or worker.state != WorkerState.IDLE:
            return None

        handler = self._handlers.get(card_id)
        if not handler:
            return None

        # Mark worker as busy
        worker.state = WorkerState.BUSY
        worker.current_task = task_id
        worker.last_active = datetime.now()

        try:
            result = await handler(action=action, **params)

            # Update stats
            worker.tasks_completed += 1
            worker.state = WorkerState.IDLE
            worker.current_task = None

            return result

        except Exception as e:
            worker.tasks_failed += 1
            worker.state = WorkerState.ERROR
            worker.current_task = None
            raise

    def release_worker(self, card_id: str):
        """Release a worker back to idle state."""
        worker = self._workers.get(card_id)
        if worker:
            worker.state = WorkerState.IDLE
            worker.current_task = None

    def set_worker_offline(self, card_id: str):
        """Mark a worker as offline."""
        worker = self._workers.get(card_id)
        if worker:
            worker.state = WorkerState.OFFLINE

    def set_worker_online(self, card_id: str):
        """Mark a worker as online (idle)."""
        worker = self._workers.get(card_id)
        if worker:
            worker.state = WorkerState.IDLE

    def get_pool_status(self) -> Dict[str, Any]:
        """Get pool status summary."""
        workers = list(self._workers.values())
        return {
            "total_workers": len(workers),
            "idle": len([w for w in workers if w.state == WorkerState.IDLE]),
            "busy": len([w for w in workers if w.state == WorkerState.BUSY]),
            "offline": len([w for w in workers if w.state == WorkerState.OFFLINE]),
            "error": len([w for w in workers if w.state == WorkerState.ERROR]),
            "workers": [w.to_dict() for w in workers],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        workers = list(self._workers.values())
        total_completed = sum(w.tasks_completed for w in workers)
        total_failed = sum(w.tasks_failed for w in workers)
        avg_duration = (
            sum(w.avg_duration_ms for w in workers) / len(workers)
            if workers else 0
        )
        return {
            "total_workers": len(workers),
            "total_completed": total_completed,
            "total_failed": total_failed,
            "avg_duration_ms": round(avg_duration, 2),
            "utilization": (
                len([w for w in workers if w.state == WorkerState.BUSY]) / len(workers)
                if workers else 0
            ),
        }
