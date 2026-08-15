"""V10 task layer — Task state model, TaskManager, global kill switch.

Sits on top of the executor (PHASE E) and owns the task lifecycle:

    QUEUED -> RUNNING -> COMPLETED / FAILED / CANCELLED

pausing at ``WAITING_FOR_CONFIRMATION`` when a LEVEL 2 step needs user
consent, and resuming via ``execute(task_id, confirmed=True)``.

The global kill switch ("JARVIS STOP" / UI stop, wired by the web layer in a
later phase) is ``task_manager.cancel_all()``: every task's stop event fires
and each in-flight step is aborted by the executor's kill-switch race.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from jarvis.core.events import Event, EventBus
from jarvis.core.events import event_bus as default_event_bus
from jarvis.core.logging import get_logger
from jarvis.core.reliability import config as reliability_config
from jarvis.tools.base import ToolResult
from jarvis.tools.executor import ExecutionContext, ToolExecutor, tool_executor

log = get_logger("jarvis.tasks")


class TaskStatus(StrEnum):
    """Lifecycle states of a task (V10 spec)."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """A unit of plan execution under TaskManager control.

    ``plan`` is duck-typed: a ``Plan`` (``jarvis/architectures/base.py``) or
    any object exposing ``.steps`` with ``.tool`` / ``.params`` attributes —
    the same shape the executor's ``execute_plan`` accepts.
    """

    user_request: str
    plan: Any
    session_id: str = ""
    agent: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TaskStatus = TaskStatus.QUEUED
    results: list[ToolResult] = field(default_factory=list)
    error: str | None = None
    stop_requested: asyncio.Event = field(default_factory=asyncio.Event)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serializable snapshot for the API / action log."""
        steps = self.plan.steps if hasattr(self.plan, "steps") else self.plan
        return {
            "id": self.id,
            "status": self.status.value,
            "user_request": self.user_request,
            "session_id": self.session_id,
            "agent": self.agent,
            "error": self.error,
            "step_count": len(list(steps)),
            "completed_steps": sum(1 for r in self.results if r.ok),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class TaskManager:
    """Owns task lifecycle, concurrency, and the global kill switch.

    Injectable for tests: pass fakes for ``executor`` / ``event_bus`` so no
    real singleton state is touched.
    """

    def __init__(
        self,
        executor: ToolExecutor | None = None,
        event_bus: EventBus | None = None,
        task_timeout: float | None = None,
        max_concurrent: int | None = None,
    ) -> None:
        self._executor = executor if executor is not None else tool_executor
        self._event_bus = event_bus if event_bus is not None else default_event_bus
        self._task_timeout = (
            task_timeout if task_timeout is not None else reliability_config.task_timeout
        )
        self._semaphore = asyncio.Semaphore(
            max_concurrent
            if max_concurrent is not None
            else reliability_config.max_concurrent_tasks
        )
        self._tasks: dict[str, Task] = {}
        self._global_stop = asyncio.Event()

    # -- registry -----------------------------------------------------------

    async def submit(
        self,
        plan: Any,
        user_request: str = "",
        session_id: str = "",
        agent: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Register a task as QUEUED and emit ``task.queued``."""
        steps = plan.steps if hasattr(plan, "steps") else plan
        if not list(steps):
            raise ValueError("plan must provide at least one step (.steps or iterable)")
        task = Task(
            user_request=user_request,
            plan=plan,
            session_id=session_id,
            agent=agent,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        await self._emit("task.queued", task)
        return task

    def get(self, task_id: str) -> Task:
        """Fetch a task by id; raises KeyError if unknown."""
        task = self._tasks.get(task_id)
        if task is None:
            raise KeyError(f"Unknown task: {task_id}")
        return task

    def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        """All tasks, oldest first, optionally filtered by status."""
        tasks = sorted(self._tasks.values(), key=lambda t: t.created_at)
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    # -- execution ----------------------------------------------------------

    async def execute(self, task_id: str, confirmed: bool = False) -> Task:
        """Run a queued task; resume a WAITING_FOR_CONFIRMATION task.

        ``confirmed=True`` satisfies LEVEL 2 decisions (used after the user
        approves the exact pending step).
        """
        task = self.get(task_id)
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise ValueError(f"Task {task_id} already finished: {task.status.value}")
        if self._global_stop.is_set():
            task.status = TaskStatus.CANCELLED
            task.error = "Global kill switch engaged"
            await self._emit("task.cancelled", task)
            return task

        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(UTC)
            task.error = None
            await self._emit("task.started", task)
            try:
                results = await asyncio.wait_for(
                    self._run_plan(task, confirmed), timeout=self._task_timeout
                )
            except TimeoutError:
                task.status = TaskStatus.FAILED
                task.error = f"Task timed out after {self._task_timeout:.0f}s"
                task.completed_at = datetime.now(UTC)
                await self._emit("task.failed", task)
                return task

        await self._classify(task, results)
        return task

    async def _run_plan(self, task: Task, confirmed: bool) -> list[ToolResult]:
        """Execute the not-yet-completed steps through the executor."""
        steps = task.plan.steps if hasattr(task.plan, "steps") else task.plan
        remaining = [s for s in steps if getattr(s, "status", "pending") != "completed"]
        results = await self._executor.execute_plan(
            remaining,
            ctx=ExecutionContext(
                session_id=task.session_id,
                task_id=task.id,
                agent=task.agent,
                stop_requested=task.stop_requested,
            ),
            confirmed=confirmed,
        )
        for step, result in zip(remaining, results):
            if hasattr(step, "status"):
                step.status = "completed" if result.ok else "failed"
            if not result.ok and hasattr(step, "error"):
                step.error = result.error
        return results

    async def _classify(self, task: Task, results: list[ToolResult]) -> None:
        """Map the executor's last result onto the task lifecycle."""
        task.results.extend(results)
        task.completed_at = datetime.now(UTC)
        last = results[-1] if results else None
        if last is None or last.ok:
            task.status = TaskStatus.COMPLETED
            await self._emit("task.completed", task)
            return
        code = last.artifacts[0].get("code", "error") if last.artifacts else "error"
        task.error = last.error
        if code == "cancelled":
            task.status = TaskStatus.CANCELLED
            await self._emit("task.cancelled", task)
        elif code == "confirmation_required":
            task.status = TaskStatus.WAITING_FOR_CONFIRMATION
            await self._emit("task.confirmation_required", task)
        else:
            task.status = TaskStatus.FAILED
            await self._emit("task.failed", task)

    # -- kill switch --------------------------------------------------------

    async def cancel(self, task_id: str) -> Task:
        """Abort one task; a running step ends as ``cancelled``."""
        task = self.get(task_id)
        task.stop_requested.set()
        if task.status in (TaskStatus.QUEUED, TaskStatus.WAITING_FOR_CONFIRMATION):
            task.status = TaskStatus.CANCELLED
            task.error = "Cancelled before execution"
            task.completed_at = datetime.now(UTC)
            await self._emit("task.cancelled", task)
        return task

    async def cancel_all(self) -> int:
        """Global kill switch: abort every task, running or queued."""
        self._global_stop.set()
        for task in self._tasks.values():
            task.stop_requested.set()
            if task.status in (TaskStatus.QUEUED, TaskStatus.WAITING_FOR_CONFIRMATION):
                task.status = TaskStatus.CANCELLED
                task.error = "Global kill switch engaged"
                task.completed_at = datetime.now(UTC)
                await self._emit("task.cancelled", task)
        return len(self._tasks)

    # -- helpers ------------------------------------------------------------

    async def _emit(self, event_type: str, task: Task) -> None:
        """Best-effort telemetry; a failing handler must never break execution."""
        data = {
            "task_id": task.id,
            "status": task.status.value,
            "user_request": task.user_request,
            "session_id": task.session_id,
            "agent": task.agent,
            "error": task.error,
        }
        if event_type == "task.confirmation_required" and task.results:
            data["step_error"] = task.results[-1].error
        try:
            await self._event_bus.emit(Event(type=event_type, data=data, source="tasks"))
        except Exception as exc:  # noqa: BLE001 — telemetry is best-effort
            log.warning("Event emit failed for %s: %s", event_type, exc)


#: Module-level singleton — the one the web layer will use.
task_manager = TaskManager()

__all__ = ["Task", "TaskManager", "TaskStatus", "task_manager"]
