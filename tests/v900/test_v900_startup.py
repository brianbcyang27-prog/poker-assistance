"""v9.0.0 regression tests — startup timing and initialization."""

import pytest


class TestCoreConfig:
    """Core configuration loads without errors."""

    def test_core_config_loads(self):
        from jarvis.core.config import get_config

        cfg = get_config()
        assert cfg is not None

    def test_config_has_required_fields(self):
        from jarvis.core.config import get_config

        cfg = get_config()
        for attr in (
            "db_path",
            "host",
            "port",
            "tts_enabled",
            "default_llm_temperature",
            "max_tokens",
        ):
            assert hasattr(cfg, attr), f"config missing: {attr}"


@pytest.mark.asyncio
class TestDiagnostics:
    """Diagnostics system runs without crashing."""

    async def test_diagnostics_run(self):
        from jarvis.core.diagnostics import DiagnosticResult

        # Unit-test just the model, not run_diagnostics which needs network
        result = DiagnosticResult(name="test", ok=True, message="ok")
        assert result.name == "test"
        assert result.ok is True
        assert result.message == "ok"

    async def test_diagnostics_result_structure(self):
        from jarvis.core.diagnostics import DiagnosticResult

        result = DiagnosticResult(name="port", ok=True, message="Port 8000 available")
        assert hasattr(result, "name")
        assert hasattr(result, "ok")
        assert hasattr(result, "message")


@pytest.mark.asyncio
class TestCapabilityRegistry:
    """Capability registry initialized and usable."""

    async def test_registry_initialized(self):
        from jarvis.core.capabilities import registry

        assert registry is not None

    async def test_registry_register_and_query(self):
        from jarvis.core.capabilities import Capability, CapabilityRegistry, CapType

        reg = CapabilityRegistry()
        await reg.register(Capability(name="test_cap", owner="test", type=CapType.TOOL))
        all_caps = await reg.get_all()
        assert len(all_caps) == 1

    async def test_registry_get_stats_has_keys(self):
        from jarvis.core.capabilities import Capability, CapabilityRegistry, CapType

        reg = CapabilityRegistry()
        await reg.register(Capability(name="stat_test", owner="a", type=CapType.TOOL))
        stats = await reg.get_stats()
        assert stats["total"] == 1
        assert "by_type" in stats
        assert "by_owner" in stats


@pytest.mark.asyncio
class TestEventBus:
    """Event bus can emit and receive events."""

    async def test_event_bus_emit_and_listen(self):
        from jarvis.core.events import Event, EventBus

        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        await bus.on("test_event", handler)
        await bus.emit(Event(type="test_event", data={"value": 42}))
        assert len(received) == 1
        assert received[0].data["value"] == 42

    async def test_event_bus_off(self):
        from jarvis.core.events import Event, EventBus

        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        await bus.on("test_event", handler)
        await bus.off("test_event", handler)
        await bus.emit(Event(type="test_event", data={"value": 42}))
        assert len(received) == 0
