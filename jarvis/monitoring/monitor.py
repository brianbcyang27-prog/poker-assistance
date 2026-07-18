"""Monitor — self-monitoring and diagnostics engine for JARVIS."""

import logging
import os
import time
import tracemalloc
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import ComponentHealth, ComponentStatus, HealthStatus, MetricSnapshot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now()


def _cpu_percent() -> float:
    """Approximate CPU usage from process times (no psutil dependency)."""
    times = os.times()
    return round((times[0] + times[1]) * 100.0 / max(times[4], 0.001), 2)


def _memory_usage_mb() -> float:
    current, _ = tracemalloc.get_traced_memory()
    return round(current / (1024 * 1024), 2)


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

class Monitor:
    """Collects metrics, checks health, diagnoses problems, and suggests fixes."""

    def __init__(self) -> None:
        self._exceptions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        self._metrics_history: Dict[str, List[MetricSnapshot]] = defaultdict(list)
        self._component_health: Dict[str, ComponentHealth] = {}

    # ------------------------------------------------------------------
    # Metric collection
    # ------------------------------------------------------------------

    async def collect_metrics(self) -> Dict[str, Any]:
        """Gather system-wide metrics."""
        mem_mb = _memory_usage_mb()
        cpu = _cpu_percent()
        metrics: Dict[str, Any] = {
            "memory_mb": mem_mb,
            "cpu_percent": cpu,
            "timestamp": _now().isoformat(),
            "component_count": len(self._component_health),
            "total_exceptions": sum(len(v) for v in self._exceptions.values()),
        }
        # Snapshot for history
        for name, value in [("memory_mb", mem_mb), ("cpu_percent", cpu)]:
            snap = MetricSnapshot(
                component="system",
                metric_name=name,
                value=value,
                unit="MB" if name == "memory_mb" else "%",
            )
            self._metrics_history["system"].append(snap)
        return metrics

    # ------------------------------------------------------------------
    # Health checks
    # ------------------------------------------------------------------

    async def check_health(self) -> HealthStatus:
        """Return an aggregated health report."""
        await self.collect_metrics()
        issues: List[str] = []
        overall = ComponentStatus.HEALTHY
        for name, ch in self._component_health.items():
            if ch.status == ComponentStatus.CRITICAL:
                overall = ComponentStatus.CRITICAL
                issues.extend(f"{name}: {i}" for i in ch.issues)
            elif ch.status == ComponentStatus.DEGRADED and overall != ComponentStatus.CRITICAL:
                overall = ComponentStatus.DEGRADED
                issues.extend(f"{name}: {i}" for i in ch.issues)
        return HealthStatus(
            overall=overall,
            components=dict(self._component_health),
            issues=issues,
            timestamp=_now(),
        )

    async def get_component_health(self, component: str) -> Dict[str, Any]:
        ch = self._component_health.get(component)
        if ch is None:
            return {"name": component, "status": "unknown", "metrics": {}, "issues": []}
        return {
            "name": ch.name,
            "status": ch.status.value,
            "metrics": ch.metrics,
            "issues": ch.issues,
            "last_check": ch.last_check.isoformat() if ch.last_check else None,
        }

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    async def track_exception(self, component: str, error: str) -> None:
        entry = {"error": error, "timestamp": _now().isoformat()}
        self._exceptions[component].append(entry)
        logger.warning("[%s] exception: %s", component, error)
        self._ensure_component(component)
        ch = self._component_health[component]
        ch.issues.append(error)
        if len(self._exceptions[component]) > 10:
            ch.status = ComponentStatus.DEGRADED
        if len(self._exceptions[component]) > 50:
            ch.status = ComponentStatus.CRITICAL

    async def track_latency(self, component: str, latency_ms: float) -> None:
        self._latencies[component].append(latency_ms)
        snap = MetricSnapshot(
            component=component,
            metric_name="latency_ms",
            value=latency_ms,
            unit="ms",
        )
        self._metrics_history[component].append(snap)
        self._ensure_component(component)
        ch = self._component_health[component]
        ch.metrics["latency_ms"] = latency_ms
        ch.last_check = _now()
        recent = self._latencies[component][-20:]
        avg = sum(recent) / len(recent)
        if avg > 5000:
            ch.status = ComponentStatus.CRITICAL
        elif avg > 1000:
            ch.status = ComponentStatus.DEGRADED

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    async def diagnose(self) -> List[Dict[str, Any]]:
        """Auto-diagnose problems across components."""
        problems: List[Dict[str, Any]] = []
        for name, ch in self._component_health.items():
            if ch.status == ComponentStatus.HEALTHY:
                continue
            problems.append({
                "component": name,
                "status": ch.status.value,
                "issues": list(ch.issues),
                "metrics": dict(ch.metrics),
            })
        return problems

    async def suggest_fixes(self) -> List[Dict[str, Any]]:
        """Suggest remediation for diagnosed problems."""
        suggestions: List[Dict[str, Any]] = []
        for name, ch in self._component_health.items():
            if ch.status == ComponentStatus.HEALTHY:
                continue
            fix = self._suggest_for_component(name, ch)
            if fix:
                suggestions.append(fix)
        return suggestions

    async def get_metrics_history(self, component: str) -> List[MetricSnapshot]:
        return list(self._metrics_history.get(component, []))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_component(self, name: str) -> None:
        if name not in self._component_health:
            self._component_health[name] = ComponentHealth(name=name, last_check=_now())

    @staticmethod
    def _suggest_for_component(name: str, ch: ComponentHealth) -> Optional[Dict[str, Any]]:
        if ch.status == ComponentStatus.CRITICAL:
            return {
                "component": name,
                "severity": "critical",
                "suggestion": f"Component '{name}' is critical. Check logs and consider restarting.",
            }
        if ch.status == ComponentStatus.DEGRADED:
            exc_count = len(ch.issues)
            if exc_count > 10:
                return {
                    "component": name,
                    "severity": "warning",
                    "suggestion": f"High exception rate in '{name}' ({exc_count}). Review recent errors.",
                }
            latency = ch.metrics.get("latency_ms")
            if latency and latency > 1000:
                return {
                    "component": name,
                    "severity": "warning",
                    "suggestion": f"High latency in '{name}' ({latency}ms). Consider optimisation.",
                }
        return None
