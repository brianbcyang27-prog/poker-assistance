"""Observability — Centralized metrics, traces, and system health monitoring.

Collects metrics from all v3.1.0 subsystems (Event Bus, Capability Registry,
Model Router, Review Pipeline, etc.) into a unified observability layer.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class Metric:
    """A single metric data point."""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict = field(default_factory=dict)


@dataclass
class TraceSpan:
    """A trace span for request tracking."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation: str
    start_time: float
    end_time: float = 0
    status: str = "ok"
    tags: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000 if self.end_time else 0

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "operation": self.operation,
            "duration_ms": round(self.duration_ms, 1),
            "status": self.status,
            "tags": self.tags,
        }


class Observability:
    """Centralized observability for all JARVIS subsystems."""

    def __init__(self):
        self._metrics: list[Metric] = []
        self._traces: dict[str, list[TraceSpan]] = {}  # trace_id -> spans
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._max_metrics = 1000
        self._max_traces = 100
        self._span_counter = 0

    # === Metrics ===

    def record_metric(self, name: str, value: float, tags: dict = None):
        """Record a metric data point."""
        self._metrics.append(Metric(name=name, value=value, tags=tags or {}))
        if len(self._metrics) > self._max_metrics:
            self._metrics = self._metrics[-self._max_metrics:]

    def increment(self, name: str, amount: int = 1):
        """Increment a counter."""
        self._counters[name] += amount

    def gauge(self, name: str, value: float):
        """Set a gauge value."""
        self._gauges[name] = value

    def get_metrics(self, name: Optional[str] = None, limit: int = 100) -> list[dict]:
        """Get recorded metrics."""
        metrics = self._metrics
        if name:
            metrics = [m for m in metrics if m.name == name]
        return [
            {"name": m.name, "value": m.value, "timestamp": m.timestamp, "tags": m.tags}
            for m in metrics[-limit:]
        ]

    def get_counters(self) -> dict:
        return dict(self._counters)

    def get_gauges(self) -> dict:
        return dict(self._gauges)

    # === Tracing ===

    def start_trace(self, operation: str, tags: dict = None) -> str:
        """Start a new trace. Returns trace_id."""
        trace_id = f"trace_{int(time.time() * 1000)}_{len(self._traces)}"
        span_id = f"span_{self._span_counter}"
        self._span_counter += 1

        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=None,
            operation=operation,
            start_time=time.time(),
            tags=tags or {},
        )
        self._traces[trace_id] = [span]
        return trace_id

    def start_span(self, trace_id: str, operation: str, parent_span_id: str = None) -> Optional[str]:
        """Start a child span within a trace."""
        if trace_id not in self._traces:
            return None

        span_id = f"span_{self._span_counter}"
        self._span_counter += 1

        span = TraceSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation=operation,
            start_time=time.time(),
        )
        self._traces[trace_id].append(span)
        return span_id

    def end_span(self, trace_id: str, span_id: str, status: str = "ok"):
        """End a span."""
        for span in self._traces.get(trace_id, []):
            if span.span_id == span_id:
                span.end_time = time.time()
                span.status = status
                break

    def end_trace(self, trace_id: str, status: str = "ok"):
        """End a trace (end all open spans)."""
        for span in self._traces.get(trace_id, []):
            if span.end_time == 0:
                span.end_time = time.time()
                span.status = status

        # Trim old traces
        if len(self._traces) > self._max_traces:
            oldest = sorted(self._traces.keys())[:len(self._traces) - self._max_traces]
            for tid in oldest:
                del self._traces[tid]

    def get_trace(self, trace_id: str) -> Optional[dict]:
        """Get a trace with all its spans."""
        spans = self._traces.get(trace_id)
        if not spans:
            return None
        total_duration = max(s.end_time for s in spans) - min(s.start_time for s in spans)
        return {
            "trace_id": trace_id,
            "spans": [s.to_dict() for s in spans],
            "total_duration_ms": round(total_duration * 1000, 1),
            "span_count": len(spans),
        }

    def get_recent_traces(self, limit: int = 20) -> list[dict]:
        """Get recent traces."""
        trace_ids = sorted(self._traces.keys(), reverse=True)[:limit]
        result = []
        for tid in trace_ids:
            trace = self.get_trace(tid)
            if trace:
                result.append(trace)
        return result

    # === System Health ===

    async def get_system_health(self) -> dict:
        """Collect health from all subsystems."""
        health = {"status": "ok", "subsystems": {}}

        # Event Bus
        try:
            from jarvis.core.events import event_bus
            stats = event_bus.get_stats()
            health["subsystems"]["event_bus"] = {
                "status": "ok",
                "emitted": stats["emit_count"],
                "errors": stats["error_count"],
            }
        except Exception as e:
            health["subsystems"]["event_bus"] = {"status": "error", "error": str(e)}

        # Capability Registry
        try:
            from jarvis.core.capabilities import registry
            stats = await registry.get_stats()
            health["subsystems"]["capabilities"] = {
                "status": "ok",
                "total": stats["total"],
            }
        except Exception as e:
            health["subsystems"]["capabilities"] = {"status": "error", "error": str(e)}

        # Model Router
        try:
            from jarvis.brain.model_router import router
            stats = router.get_routing_stats()
            health["subsystems"]["model_router"] = {
                "status": "ok",
                "routings": stats["total_routings"],
                "models": len(stats["models"]),
            }
        except Exception as e:
            health["subsystems"]["model_router"] = {"status": "error", "error": str(e)}

        # ACI
        try:
            from jarvis.brain.aci import aci
            stats = aci.get_stats()
            health["subsystems"]["aci"] = {
                "status": "ok",
                "messages": stats["total_messages"],
            }
        except Exception as e:
            health["subsystems"]["aci"] = {"status": "error", "error": str(e)}

        # DAG Planner
        try:
            from jarvis.brain.dag_planner import dag_planner
            stats = dag_planner.get_stats()
            health["subsystems"]["dag_planner"] = {
                "status": "ok",
                "missions": stats["total_missions"],
            }
        except Exception as e:
            health["subsystems"]["dag_planner"] = {"status": "error", "error": str(e)}

        # Overall status
        has_error = any(
            s.get("status") == "error" for s in health["subsystems"].values()
        )
        health["status"] = "degraded" if has_error else "ok"

        return health


# Module-level singleton
observability = Observability()
