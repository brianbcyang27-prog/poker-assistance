"""Event Bus — Async pub/sub for decoupled component communication.

Every JARVIS component emits and consumes events through this bus.
No component knows about other components directly.

Usage:
    from jarvis.core.events import event_bus, Event

    # Subscribe
    await event_bus.on("task.completed", my_handler)

    # Emit
    await event_bus.emit(Event(type="task.completed", data={...}))

    # One-shot listener
    await event_bus.once("mission.completed", cleanup)

    # Wildcard
    await event_bus.on("task.*", all_task_handler)
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

log = logging.getLogger("jarvis.events")

Handler = Callable[["Event"], Coroutine[Any, Any, None]]


@dataclass
class Event:
    """An event flowing through the bus."""

    type: str
    data: dict = field(default_factory=dict)
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.type}:{int(self.timestamp * 1000)}"

    def __repr__(self):
        return f"Event({self.type}, source={self.source}, keys={list(self.data.keys())})"


class EventBus:
    """In-process async event bus with wildcard support.

    Features:
    - Wildcard subscriptions: "task.*" matches "task.completed", "task.failed"
    - One-shot listeners: auto-remove after first fire
    - History buffer: last N events for debugging/replay
    - Metric tracking: emit count, handler count, error count
    """

    def __init__(self, history_size: int = 100):
        self._handlers: dict[str, list[Handler]] = {}
        self._once_handlers: dict[str, list[Handler]] = {}
        self._history: list[Event] = []
        self._history_size = history_size
        self._emit_count = 0
        self._error_count = 0
        self._lock = asyncio.Lock()

    async def on(self, event_type: str, handler: Handler) -> None:
        """Subscribe to an event type. Supports wildcards like 'task.*'."""
        async with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            log.debug(f"Subscribed to '{event_type}': {handler.__qualname__}")

    async def once(self, event_type: str, handler: Handler) -> None:
        """Subscribe to an event type, auto-remove after first fire."""
        async with self._lock:
            if event_type not in self._once_handlers:
                self._once_handlers[event_type] = []
            self._once_handlers[event_type].append(handler)
            log.debug(f"Once-subscribed to '{event_type}': {handler.__qualname__}")

    async def off(self, event_type: str, handler: Handler) -> None:
        """Unsubscribe a handler from an event type."""
        async with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [
                    h for h in self._handlers[event_type] if h != handler
                ]
            if event_type in self._once_handlers:
                self._once_handlers[event_type] = [
                    h for h in self._once_handlers[event_type] if h != handler
                ]

    async def emit(self, event: Event) -> None:
        """Emit an event to all matching subscribers."""
        self._emit_count += 1

        # Record in history
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history = self._history[-self._history_size :]

        # Find matching handlers
        handlers = self._get_matching_handlers(event.type)

        # Collect once handlers and clear them
        once_handlers = self._get_matching_once(event.type)

        all_handlers = handlers + once_handlers

        if not all_handlers:
            log.debug(f"No handlers for '{event.type}'")
            return

        log.debug(f"Emitting '{event.type}' to {len(all_handlers)} handlers")

        # Fire all handlers concurrently
        tasks = []
        for handler in all_handlers:
            tasks.append(self._safe_call(handler, event))
        await asyncio.gather(*tasks)

    def _get_matching_handlers(self, event_type: str) -> list[Handler]:
        """Get all handlers matching an event type (exact + wildcard)."""
        result = []
        # Exact match
        if event_type in self._handlers:
            result.extend(self._handlers[event_type])
        # Wildcard matches: "task.*" matches "task.completed"
        for pattern, handlers in self._handlers.items():
            if pattern != event_type and self._matches(pattern, event_type):
                result.extend(handlers)
        return result

    def _get_matching_once(self, event_type: str) -> list[Handler]:
        """Get once-handlers matching event type, then remove them."""
        result = []
        to_remove = []
        for pattern, handlers in self._once_handlers.items():
            matched = [h for h in handlers if self._matches(pattern, event_type)]
            if matched:
                result.extend(matched)
                to_remove.append((pattern, matched))

        for pattern, matched in to_remove:
            self._once_handlers[pattern] = [
                h for h in self._once_handlers.get(pattern, []) if h not in matched
            ]
        return result

    @staticmethod
    def _matches(pattern: str, event_type: str) -> bool:
        """Check if a wildcard pattern matches an event type."""
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix + ".")
        if pattern == "*.*":
            return "." in event_type
        return pattern == event_type

    async def _safe_call(self, handler: Handler, event: Event) -> None:
        """Call a handler, catching and logging errors."""
        try:
            await handler(event)
        except Exception as e:
            self._error_count += 1
            log.error(f"Handler {handler.__qualname__} failed for '{event.type}': {e}")

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> list[Event]:
        """Get event history, optionally filtered by type."""
        events = self._history
        if event_type:
            events = [e for e in events if self._matches(event_type, e.type)]
        return events[-limit:]

    def get_stats(self) -> dict:
        """Get bus statistics."""
        total_handlers = sum(len(h) for h in self._handlers.values())
        total_once = sum(len(h) for h in self._once_handlers.values())
        return {
            "emit_count": self._emit_count,
            "error_count": self._error_count,
            "handler_count": total_handlers + total_once,
            "subscriptions": {k: len(v) for k, v in self._handlers.items()},
            "history_size": len(self._history),
        }

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()


# Module-level singleton
event_bus = EventBus()
