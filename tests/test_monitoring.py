"""Tests for JARVIS Monitoring engine (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.monitoring import (
    Monitor,
    HealthStatus,
    MetricSnapshot,
    ComponentHealth,
    ComponentStatus,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestMonitoringModels:
    def test_component_status(self):
        assert ComponentStatus.HEALTHY.value == "healthy"
        assert ComponentStatus.DEGRADED.value == "degraded"
        assert ComponentStatus.CRITICAL.value == "critical"

    def test_metric_snapshot(self):
        snap = MetricSnapshot(component="cpu", metric_name="usage", value=45.2, unit="%")
        assert snap.component == "cpu"
        assert snap.value == 45.2
        assert snap.unit == "%"

    def test_component_health(self):
        ch = ComponentHealth(
            name="brain", status=ComponentStatus.HEALTHY,
            metrics={"latency_ms": 50.0}, issues=[],
        )
        assert ch.name == "brain"
        assert ch.status == ComponentStatus.HEALTHY

    def test_health_status(self):
        hs = HealthStatus(overall=ComponentStatus.DEGRADED)
        assert hs.overall == ComponentStatus.DEGRADED
        assert hs.components == {}


# ════════════════════════════════════════════════════════════
# Monitor Tests
# ════════════════════════════════════════════════════════════

class TestMonitor:
    def setup_method(self):
        self.monitor = Monitor()

    def test_collect_metrics(self):
        metrics = _run(self.monitor.collect_metrics())
        assert isinstance(metrics, dict)
        assert "memory_mb" in metrics
        assert "cpu_percent" in metrics
        assert "timestamp" in metrics
        assert "component_count" in metrics

    def test_check_health(self):
        health = _run(self.monitor.check_health())
        assert isinstance(health, HealthStatus)
        assert health.overall == ComponentStatus.HEALTHY
        assert isinstance(health.components, dict)

    def test_track_exception(self):
        _run(self.monitor.track_exception("brain", "Test error"))
        result = _run(self.monitor.get_component_health("brain"))
        assert result["name"] == "brain"
        assert "Test error" in result["issues"]

    def test_track_exception_degraded(self):
        for i in range(15):
            _run(self.monitor.track_exception("brain", f"Error {i}"))
        result = _run(self.monitor.get_component_health("brain"))
        assert result["status"] == "degraded"

    def test_track_exception_critical(self):
        for i in range(55):
            _run(self.monitor.track_exception("brain", f"Error {i}"))
        result = _run(self.monitor.get_component_health("brain"))
        assert result["status"] == "critical"

    def test_track_latency(self):
        _run(self.monitor.track_latency("api", 150.0))
        result = _run(self.monitor.get_component_health("api"))
        assert result["metrics"]["latency_ms"] == 150.0

    def test_track_latency_high(self):
        for _ in range(25):
            _run(self.monitor.track_latency("api", 6000.0))
        result = _run(self.monitor.get_component_health("api"))
        assert result["status"] == "critical"

    def test_get_component_health_unknown(self):
        result = _run(self.monitor.get_component_health("nonexistent"))
        assert result["status"] == "unknown"

    def test_diagnose(self):
        _run(self.monitor.track_exception("brain", "Error"))
        problems = _run(self.monitor.diagnose())
        assert isinstance(problems, list)

    def test_suggest_fixes(self):
        _run(self.monitor.track_exception("brain", "Error"))
        for i in range(15):
            _run(self.monitor.track_exception("brain", f"Err {i}"))
        fixes = _run(self.monitor.suggest_fixes())
        assert isinstance(fixes, list)
        assert len(fixes) > 0
        for fix in fixes:
            assert "component" in fix
            assert "suggestion" in fix

    def test_metrics_history(self):
        _run(self.monitor.track_latency("api", 100.0))
        history = _run(self.monitor.get_metrics_history("api"))
        assert isinstance(history, list)
        assert len(history) == 1
        assert history[0].value == 100.0
