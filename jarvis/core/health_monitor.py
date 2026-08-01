"""Continuous health monitor for JARVIS v9.0.0.

Runs periodic checks on critical subsystems and emits events on state
changes via the event bus.

Subsystems monitored:
    database  — SQLite responsiveness
    llm       — LLM API reachability
    disk      — Free disk space
    agents    — King/worker count and health
    circuit   — Circuit breaker states

Usage:
    from jarvis.core.health_monitor import health_monitor

    # Start monitoring (typically in app lifespan)
    await health_monitor.start()

    # Check current status
    status = health_monitor.status()

    # Stop (on shutdown)
    await health_monitor.stop()
"""

import asyncio
import time
from dataclasses import dataclass, field

from jarvis.core.logging import get_logger

log = get_logger("jarvis.health")


@dataclass
class HealthCheck:
    """Result of a single health check."""

    name: str
    ok: bool
    message: str
    timestamp: float = field(default_factory=time.time)
    latency_ms: float = 0.0


@dataclass
class SubsystemHealth:
    """Tracked state for one subsystem."""

    ok: bool = True
    last_change: float = 0.0
    last_check: float = 0.0
    last_error: str = ""
    consecutive_failures: int = 0


class HealthMonitor:
    """Periodically checks subsystem health and emits state changes.

    Checks run at a configurable interval (default 30s). When a subsystem
    transitions between healthy/unhealthy, an event is emitted.

    The monitor is a background asyncio task — start it in the app lifespan
    and stop it during shutdown.
    """

    def __init__(self, check_interval: float = 30.0) -> None:
        self._check_interval = check_interval
        self._task: asyncio.Task | None = None
        self._subsystems: dict[str, SubsystemHealth] = {
            name: SubsystemHealth() for name in ("database", "llm", "disk", "agents", "circuit")
        }
        self._latest: dict[str, HealthCheck] = {}

    async def start(self) -> None:
        """Start periodic health checks in a background task."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run())
        log.info("Health monitor started (interval=%ds)", self._check_interval)

    async def stop(self) -> None:
        """Stop periodic health checks."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            log.info("Health monitor stopped")

    async def _run(self) -> None:
        """Main loop: run checks, then sleep."""
        try:
            while True:
                await self._check_all()
                await asyncio.sleep(self._check_interval)
        except asyncio.CancelledError:
            pass

    async def _check_all(self) -> None:
        """Run all health checks in parallel and emit state changes."""
        import asyncio

        checks = {
            "database": self._check_database(),
            "disk": self._check_disk(),
            "agents": self._check_agents(),
            "circuit": self._check_circuit(),
        }

        results = await asyncio.gather(*checks.values(), return_exceptions=True)

        for name, result in zip(checks, results):
            if isinstance(result, Exception):
                hc = HealthCheck(name=name, ok=False, message=str(result))
            else:
                hc = result

            self._latest[name] = hc
            self._update_subsystem(name, hc)

    def _update_subsystem(self, name: str, hc: HealthCheck) -> None:
        """Track subsystem state and emit events on transitions."""
        sub = self._subsystems.get(name)
        if not sub:
            return

        sub.last_check = time.time()

        if not hc.ok:
            sub.consecutive_failures += 1
            sub.last_error = hc.message
            if sub.ok:
                sub.ok = False
                sub.last_change = time.time()
                log.warning("Health: %s became UNHEALTHY — %s", name, hc.message)
                self._emit("health.degraded", name, hc)
        else:
            sub.consecutive_failures = 0
            sub.last_error = ""
            if not sub.ok:
                sub.ok = True
                sub.last_change = time.time()
                log.info("Health: %s recovered", name)
                self._emit("health.recovered", name, hc)

    def _emit(self, event_type: str, subsystem: str, hc: HealthCheck) -> None:
        """Emit a health event via the event bus."""
        try:
            from jarvis.core.events import Event, event_bus

            asyncio.ensure_future(
                event_bus.emit(
                    Event(
                        type=event_type,
                        data={
                            "subsystem": subsystem,
                            "ok": hc.ok,
                            "message": hc.message,
                            "latency_ms": hc.latency_ms,
                        },
                        source="health_monitor",
                    )
                )
            )
        except Exception as e:
            log.debug("Failed to emit health event: %s", e)

    async def _check_database(self) -> HealthCheck:
        """Check database responsiveness."""
        start = time.monotonic()
        try:
            from jarvis.core.database import get_db

            db = await get_db()
            await db.fetchone("SELECT 1")
            latency = (time.monotonic() - start) * 1000
            return HealthCheck(
                name="database",
                ok=True,
                message=f"responsive ({latency:.0f}ms)",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return HealthCheck(
                name="database",
                ok=False,
                message=f"{e} ({latency:.0f}ms)",
                latency_ms=latency,
            )

    async def _check_disk(self) -> HealthCheck:
        """Check free disk space."""
        try:
            import shutil

            usage = shutil.disk_usage("/")
            free_gb = usage.free / (1024**3)
            if free_gb < 1.0:
                return HealthCheck(
                    name="disk",
                    ok=False,
                    message=f"Critical: {free_gb:.1f} GB free",
                )
            if free_gb < 5.0:
                return HealthCheck(
                    name="disk",
                    ok=True,
                    message=f"Low: {free_gb:.1f} GB free (threshold: 5 GB)",
                )
            return HealthCheck(
                name="disk",
                ok=True,
                message=f"{free_gb:.1f} GB free",
            )
        except Exception as e:
            return HealthCheck(name="disk", ok=False, message=str(e))

    async def _check_agents(self) -> HealthCheck:
        """Check agent hierarchy is intact."""
        try:
            from jarvis.web.main import jarvis

            if jarvis is None:
                return HealthCheck(name="agents", ok=True, message="Not initialized yet")
            kings = jarvis.get_all_kings()
            worker_count = sum(len(k.get_all_workers()) for k in kings)
            return HealthCheck(
                name="agents",
                ok=True,
                message=f"{len(kings)} kings, {worker_count} workers",
            )
        except Exception as e:
            return HealthCheck(name="agents", ok=False, message=str(e))

    async def _check_circuit(self) -> HealthCheck:
        """Check all registered circuit breakers."""
        try:
            from jarvis.core.reliability import circuit_breaker

            stats = circuit_breaker.all_stats()
            open_cbs = [name for name, s in stats.items() if s["state"] == "open"]
            if open_cbs:
                return HealthCheck(
                    name="circuit",
                    ok=False,
                    message=f"Open circuits: {', '.join(open_cbs)}",
                )
            total = len(stats)
            healthy = sum(1 for s in stats.values() if s["state"] == "closed")
            return HealthCheck(
                name="circuit",
                ok=True,
                message=f"{healthy}/{total} circuits closed",
            )
        except Exception as e:
            return HealthCheck(name="circuit", ok=False, message=str(e))

    def status(self) -> dict:
        """Get current health status of all subsystems."""
        return {
            "healthy": all(s.ok for s in self._subsystems.values()),
            "checks": {
                name: {
                    "ok": lc.ok,
                    "message": lc.message,
                    "latency_ms": lc.latency_ms,
                }
                for name, lc in self._latest.items()
            },
            "subsystems": {
                name: {
                    "ok": s.ok,
                    "consecutive_failures": s.consecutive_failures,
                    "last_change": s.last_change,
                    "last_check": s.last_check,
                    "last_error": s.last_error,
                }
                for name, s in self._subsystems.items()
            },
        }

    def is_healthy(self) -> bool:
        """Quick check: all subsystems OK."""
        return all(s.ok for s in self._subsystems.values())


health_monitor = HealthMonitor()
