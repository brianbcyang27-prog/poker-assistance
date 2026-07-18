"""Task Orchestrator — King→Worker delegation and parallel execution."""

import asyncio
import time
import uuid
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

log = logging.getLogger("jarvis.orchestration")


class TaskStatus(str, Enum):
    """Status of a delegated task."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(str, Enum):
    """Priority levels for tasks."""
    CRITICAL = "critical"  # Must run now
    HIGH = "high"          # Run soon
    NORMAL = "normal"      # Standard queue
    LOW = "low"            # Run when idle
    BACKGROUND = "background"  # Run in background


@dataclass
class DelegatedTask:
    """A task delegated from a King to a Worker."""
    id: str = ""
    name: str = ""
    description: str = ""
    king: str = ""           # Card ID of delegating King (e.g., "♥K")
    worker: str = ""         # Card ID of assigned Worker (e.g., "♥Q")
    worker_name: str = ""    # Human-readable worker name
    action: str = ""         # Action to execute
    params: Dict[str, Any] = field(default_factory=dict)
    priority: str = TaskPriority.NORMAL
    status: str = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"task_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "king": self.king,
            "worker": self.worker,
            "worker_name": self.worker_name,
            "action": self.action,
            "params": self.params,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
        }


class TaskOrchestrator:
    """Orchestrates King→Worker task delegation.

    Flow:
        1. King creates a DelegatedTask
        2. Orchestrator assigns to appropriate Worker
        3. Worker executes the action
        4. Result flows back to King
        5. King reports to User

    Supports:
        - Parallel execution (multiple workers simultaneously)
        - Priority queuing
        - Retry with backoff
        - Timeout handling
        - Task cancellation
    """

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._tasks: Dict[str, DelegatedTask] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running: Dict[str, asyncio.Task] = {}
        self._handlers: Dict[str, Callable] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._stats = {
            "total_delegated": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
        }

    def register_handler(self, action: str, handler: Callable):
        """Register a handler for a specific action type."""
        self._handlers[action] = handler

    async def delegate(
        self,
        name: str,
        king: str,
        worker: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        priority: str = TaskPriority.NORMAL,
        timeout: int = 300,
        description: str = "",
    ) -> DelegatedTask:
        """Delegate a task from a King to a Worker.

        Args:
            name: Human-readable task name
            king: Card ID of delegating King
            worker: Card ID of target Worker
            action: Action to execute
            params: Action parameters
            priority: Task priority
            timeout: Timeout in seconds
            description: Task description

        Returns:
            DelegatedTask with initial state
        """
        task = DelegatedTask(
            name=name,
            description=description,
            king=king,
            worker=worker,
            action=action,
            params=params or {},
            priority=priority,
            timeout_seconds=timeout,
        )

        self._tasks[task.id] = task
        self._stats["total_delegated"] += 1

        # Queue for execution
        priority_value = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
            TaskPriority.BACKGROUND: 4,
        }.get(priority, 2)

        await self._queue.put((priority_value, task.id))
        task.status = TaskStatus.QUEUED

        log.info(f"Delegated task {task.id}: {name} → {worker} ({action})")
        return task

    async def execute_next(self) -> Optional[DelegatedTask]:
        """Execute the next task in the queue.

        Returns:
            Completed DelegatedTask or None if queue is empty
        """
        try:
            priority, task_id = await asyncio.wait_for(
                self._queue.get(), timeout=0.1
            )
        except asyncio.TimeoutError:
            return None

        task = self._tasks.get(task_id)
        if not task or task.status == TaskStatus.CANCELLED:
            return None

        # Execute with semaphore for concurrency control
        async with self._semaphore:
            return await self._execute_task(task)

    async def execute_parallel(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[DelegatedTask]:
        """Execute multiple tasks in parallel.

        Args:
            tasks: List of task dicts with name, king, worker, action, params

        Returns:
            List of completed DelegatedTasks
        """
        delegated = []
        for task_spec in tasks:
            task = await self.delegate(**task_spec)
            delegated.append(task)

        # Execute all in parallel
        coros = [self._execute_task(t) for t in delegated]
        results = await asyncio.gather(*coros, return_exceptions=True)

        return [r for r in results if isinstance(r, DelegatedTask)]

    async def _execute_task(self, task: DelegatedTask) -> DelegatedTask:
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        handler = self._handlers.get(task.action)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler registered for action: {task.action}"
            self._stats["total_failed"] += 1
            return task

        try:
            # Create asyncio task with timeout
            result = await asyncio.wait_for(
                handler(**task.params),
                timeout=task.timeout_seconds,
            )

            task.result = result
            task.status = TaskStatus.COMPLETED
            self._stats["total_completed"] += 1

        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = f"Task timed out after {task.timeout_seconds}s"
            self._stats["total_failed"] += 1

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._stats["total_failed"] += 1

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                delay = min(2 ** task.retry_count, 30)
                log.info(f"Retrying task {task.id} in {delay}s (attempt {task.retry_count})")
                await asyncio.sleep(delay)
                return await self._execute_task(task)

        finally:
            task.completed_at = datetime.now()
            if task.started_at:
                task.duration_ms = (task.completed_at - task.started_at).total_seconds() * 1000

        return task

    async def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        task = self._tasks.get(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False

        task.status = TaskStatus.CANCELLED
        self._stats["total_cancelled"] += 1

        # Cancel asyncio task if running
        if task_id in self._running:
            self._running[task_id].cancel()
            del self._running[task_id]

        return True

    def get_task(self, task_id: str) -> Optional[DelegatedTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_tasks_by_status(self, status: str) -> List[DelegatedTask]:
        """Get all tasks with a specific status."""
        return [t for t in self._tasks.values() if t.status == status]

    def get_tasks_by_king(self, king: str) -> List[DelegatedTask]:
        """Get all tasks delegated by a specific King."""
        return [t for t in self._tasks.values() if t.king == king]

    def get_tasks_by_worker(self, worker: str) -> List[DelegatedTask]:
        """Get all tasks assigned to a specific Worker."""
        return [t for t in self._tasks.values() if t.worker == worker]

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics."""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "running": len(self._running),
            "total_tasks": len(self._tasks),
            "max_concurrent": self.max_concurrent,
        }

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all active (non-terminal) tasks."""
        return [
            t.to_dict()
            for t in self._tasks.values()
            if t.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)
        ]
