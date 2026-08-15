"""V10 tool executor — permission-gated, timeout-bounded, kill-switch-aware.

Wraps ``jarvis.tools.registry.tool_registry`` (PHASE C) with the three controls
the V10 spec requires around every tool call:

* **Permission gate** — every step resolves through ``permission_manager``
  (PHASE D). LEVEL 2 blocks until the caller re-runs with ``confirmed=True``;
  LEVEL 3 and Trinity DENY block outright. Structured decisions are attached
  to the result for the action log.
* **Timeout** — each step runs under ``self.timeout`` seconds (default 30).
* **Kill switch** — ``ExecutionContext.stop_requested`` (an ``asyncio.Event``
  wired to the V10 "JARVIS STOP" / UI stop in PHASE F) aborts before and during
  runs, surfacing a ``cancelled`` result instead of executing.

Iteration budget: the V10 spec's ``MAX_TOOL_STEPS = 20`` deliberately overrides
``ReliabilityConfig.max_tool_iterations`` (5), which is tuned for agent loops
rather than plan execution. The override is explicit and documented here so the
two budgets never silently diverge.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.events import Event, EventBus
from jarvis.core.events import event_bus as default_event_bus
from jarvis.core.logging import get_logger
from jarvis.tools.base import ToolResult
from jarvis.tools.permissions import PermissionManager, permission_manager
from jarvis.tools.registry import ToolRegistry, tool_registry

log = get_logger("jarvis.tools.executor")

#: V10 spec budget for one plan execution (docs/JARVIS_V10_MASTER_PLAN.md).
MAX_TOOL_STEPS = 20
#: Per-step wall-clock budget in seconds.
DEFAULT_TOOL_TIMEOUT = 30.0


@dataclass
class ExecutionContext:
    """Per-execution state threaded through every step.

    Attributes:
        session_id: The chat / mission session this execution belongs to.
        task_id: The V10 Task this execution serves (set by the task layer).
        agent: Which agent requested the tools (audit trail).
        stop_requested: Kill-switch event; when set, no further steps run and
            in-flight steps are cancelled.
        extra: Free-form context passed to the permission system.
    """

    session_id: str = ""
    task_id: str = ""
    agent: str = ""
    stop_requested: asyncio.Event | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ToolExecutor:
    """Runs registered tools with permission gating, timeouts, and a kill switch.

    Injectable for tests: pass fakes for ``registry`` / ``permissions`` /
    ``event_bus`` so no real singleton state is touched.
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        permissions: PermissionManager | None = None,
        max_steps: int = MAX_TOOL_STEPS,
        timeout: float = DEFAULT_TOOL_TIMEOUT,
        event_bus: EventBus | None = None,
    ) -> None:
        self._registry = registry if registry is not None else tool_registry
        self._permissions = permissions if permissions is not None else permission_manager
        self._max_steps = max(1, int(max_steps))
        self._timeout = max(0.1, float(timeout))
        self._event_bus = event_bus if event_bus is not None else default_event_bus

    @property
    def max_steps(self) -> int:
        """Effective per-plan step budget (V10 MAX_TOOL_STEPS)."""
        return self._max_steps

    @property
    def timeout(self) -> float:
        """Per-step timeout in seconds."""
        return self._timeout

    # -- execution -----------------------------------------------------------

    async def execute_step(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
        ctx: ExecutionContext | None = None,
        confirmed: bool = False,
    ) -> ToolResult:
        """Execute a single tool with permission gate, timeout, kill switch.

        Args:
            tool_name: Registered executable tool name.
            params: Parameters for the tool.
            ctx: Execution context (kill switch, identity). A fresh one is used
                when omitted.
            confirmed: Pass True to satisfy LEVEL 2 (CONFIRMATION) decisions
                after the user has explicitly approved this exact action.

        Returns:
            ToolResult — never raises (except caller-initiated cancellation).
        """
        ctx = ctx or ExecutionContext()
        params = params or {}

        if self._is_stopped(ctx):
            return self._failure(tool_name, "JARVIS STOP received before execution", "cancelled")

        tool = self._registry.get_executable(tool_name)
        if tool is None:
            return self._failure(tool_name, f"Unknown tool: {tool_name}", "not_found")

        decision = self._permissions.check_tool(
            tool.spec,
            command=params.get("command", ""),
            agent=ctx.agent,
            context=ctx.extra or None,
        )
        if not decision.allowed:
            return self._failure(
                tool_name,
                decision.reason or "Permission denied",
                "permission_denied",
                recoverable=decision.requires_confirmation or decision.requires_approval,
                artifacts=[decision.to_dict()],
            )
        if decision.requires_confirmation and not confirmed:
            return self._failure(
                tool_name,
                "LEVEL 2 (confirmation): re-run with confirmed=True after user consent",
                "confirmation_required",
                artifacts=[decision.to_dict()],
            )

        await self._emit(
            "tool.started",
            {
                "tool": tool_name,
                "params": params,
                "session_id": ctx.session_id,
                "task_id": ctx.task_id,
                "agent": ctx.agent,
            },
        )

        start = time.monotonic()
        # Race the tool against the kill switch and the timeout so a mid-run
        # stop is honored without waiting for the step to finish.
        run_task = asyncio.create_task(self._registry.execute(tool_name, params))
        stop_task = None
        if ctx.stop_requested is not None:
            stop_task = asyncio.create_task(ctx.stop_requested.wait())
        watch = [run_task] if stop_task is None else [run_task, stop_task]
        try:
            done, _ = await asyncio.wait(
                watch, timeout=self._timeout, return_when=asyncio.FIRST_COMPLETED
            )
        except asyncio.CancelledError:
            # The executor's own caller cancelled this step — clean up and propagate.
            run_task.cancel()
            if stop_task is not None:
                stop_task.cancel()
            raise

        if run_task not in done:
            run_task.cancel()
            if stop_task is not None and stop_task in done:
                await self._emit(
                    "tool.failed",
                    {"tool": tool_name, "ok": False, "error": "cancelled", "task_id": ctx.task_id},
                )
                return self._failure(
                    tool_name, "JARVIS STOP received during execution", "cancelled"
                )
            await self._emit(
                "tool.failed",
                {"tool": tool_name, "ok": False, "error": "timeout", "task_id": ctx.task_id},
            )
            return self._failure(
                tool_name, f"Tool timed out after {self._timeout:.1f}s", "timeout"
            )

        if stop_task is not None and not stop_task.done():
            stop_task.cancel()
        try:
            result = run_task.result()
        except asyncio.CancelledError:
            if self._is_stopped(ctx):
                await self._emit(
                    "tool.failed",
                    {"tool": tool_name, "ok": False, "error": "cancelled", "task_id": ctx.task_id},
                )
                return self._failure(
                    tool_name, "JARVIS STOP received during execution", "cancelled"
                )
            raise
        except TimeoutError:
            return self._failure(
                tool_name, f"Tool timed out after {self._timeout:.1f}s", "timeout"
            )

        result.duration_ms = (time.monotonic() - start) * 1000
        result.tool = result.tool or tool_name
        await self._emit(
            "tool.completed" if result.ok else "tool.failed",
            {
                "tool": tool_name,
                "ok": result.ok,
                "duration_ms": result.duration_ms,
                "error": result.error,
                "task_id": ctx.task_id,
            },
        )
        return result

    async def execute_plan(
        self,
        plan: Any,
        ctx: ExecutionContext | None = None,
        confirmed: bool = False,
    ) -> list[ToolResult]:
        """Execute every step of a plan under the MAX_TOOL_STEPS budget.

        ``plan`` is either a ``Plan``/``list`` of step-like objects exposing
        ``.tool`` (tool name) and ``.params`` (dict), or a ``Plan`` with a
        ``.steps`` sequence (PHASE F task layer hands over real PlanStep
        objects — duck-typed here to avoid a hard dependency).

        Execution stops on the first failed step, when the step budget is
        exhausted, or when the kill switch is set. The step that triggered the
        stop is included as the last item of ``results``.
        """
        ctx = ctx or ExecutionContext()
        steps = list(plan.steps if hasattr(plan, "steps") else plan)
        results: list[ToolResult] = []

        for index, step in enumerate(steps):
            if self._is_stopped(ctx):
                results.append(
                    self._failure(
                        getattr(step, "tool", "<plan>"),
                        "JARVIS STOP received; plan aborted",
                        "cancelled",
                    )
                )
                break
            if len(results) >= self._max_steps:
                results.append(
                    self._failure(
                        getattr(step, "tool", "<plan>"),
                        f"Max tool steps ({self._max_steps}) exceeded",
                        "max_steps",
                    )
                )
                break

            result = await self.execute_step(
                step.tool,
                dict(getattr(step, "params", None) or {}),
                ctx=ctx,
                confirmed=confirmed,
            )
            results.append(result)
            if not result.ok:
                break

        return results

    # -- helpers -------------------------------------------------------------

    def _is_stopped(self, ctx: ExecutionContext) -> bool:
        return ctx.stop_requested is not None and ctx.stop_requested.is_set()

    def _failure(
        self,
        tool_name: str,
        error: str,
        code: str,
        recoverable: bool = True,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> ToolResult:
        return ToolResult(
            ok=False,
            error=error,
            tool=tool_name,
            errors=[error],
            artifacts=[
                {
                    "type": "error",
                    "code": code,
                    "message": error,
                    "recoverable": recoverable,
                }
            ]
            + (artifacts or []),
            recovery=f"Tool '{tool_name}' blocked/failed: {code}" if recoverable else None,
        )

    async def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit telemetry; a failing handler must never break execution."""
        try:
            await self._event_bus.emit(
                Event(type=event_type, data=data, source="executor")
            )
        except Exception as exc:  # noqa: BLE001 — telemetry is best-effort
            log.warning("Event emit failed for %s: %s", event_type, exc)


#: Module-level singleton — the one the task layer (PHASE F) will use.
tool_executor = ToolExecutor()

__all__ = [
    "MAX_TOOL_STEPS",
    "DEFAULT_TOOL_TIMEOUT",
    "ExecutionContext",
    "ToolExecutor",
    "tool_executor",
]
