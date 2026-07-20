"""v6.3.0 integration tests — Unified AI Operating System."""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

loop = asyncio.get_event_loop()


# ── Unified Tool Layer ──────────────────────────────────────────────

class TestUnifiedToolLayer:
    """Test the unified tool interface (Phase 1)."""

    def test_import_tool(self):
        from jarvis.tools import tool
        assert tool is not None

    def test_list_tools(self):
        from jarvis.tools import tool
        tools = tool.list_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 20

    def test_get_tool_info(self):
        from jarvis.tools import tool
        info = tool.get_tool_info("search_web")
        assert info is not None
        assert "name" in info
        assert info["name"] == "search_web"

    def test_get_tool_info_nonexistent(self):
        from jarvis.tools import tool
        info = tool.get_tool_info("nonexistent_xyz")
        assert info is None

    def test_tool_result_success(self):
        from jarvis.tools.result import ToolResult
        r = ToolResult(ok=True, data={"url": "https://example.com"})
        assert r.ok is True
        assert r.data["url"] == "https://example.com"
        d = r.to_dict()
        assert d["ok"] is True

    def test_tool_result_failure(self):
        from jarvis.tools.result import ToolResult
        r = ToolResult(ok=False, error="timeout")
        assert r.ok is False
        assert r.error == "timeout"

    def test_tool_result_no_data(self):
        from jarvis.tools.result import ToolResult
        r = ToolResult(ok=True)
        d = r.to_dict()
        assert d["ok"] is True
        assert d["data"] is None

    def test_timed_decorator(self):
        from jarvis.tools.result import timed
        import time as t

        @timed
        async def fast_fn():
            t.sleep(0.01)
            return 42

        result = loop.run_until_complete(fast_fn())
        assert result.ok is True
        assert result.tool == "fast_fn"

    def test_tool_has_all_categories(self):
        from jarvis.tools import tool
        tools = tool.list_tools()
        categories = {"web", "browser", "vision", "accessibility", "terminal", "file", "computer", "memory", "engineering", "mission"}
        found = set()
        for t_name in tools:
            for cat in categories:
                if cat in t_name:
                    found.add(cat)
                    break
        # Should have tools in multiple categories
        assert len(found) >= 5


# ── Unified Context Engine ──────────────────────────────────────────

class TestUnifiedContext:
    """Test the context engine (Phase 3).

    Note: build_context/inject_context are async and require DB + full brain.
    We test the non-blocking parts only; integration tests are in a separate run.
    """

    def test_context_engine_import(self):
        from jarvis.brain.core.context import BrainContextManager
        ctx = BrainContextManager()
        assert ctx is not None

    def test_context_engine_has_methods(self):
        from jarvis.brain.core.context import BrainContextManager
        ctx = BrainContextManager()
        assert hasattr(ctx, "build_context")
        assert hasattr(ctx, "inject_context")
        assert hasattr(ctx, "get_preferences")
        assert hasattr(ctx, "get_relevant_memories")
        assert hasattr(ctx, "get_mission_history")
        assert hasattr(ctx, "get_execution_history")
        assert hasattr(ctx, "get_working_memory_context")


# ── Reliability Configuration ──────────────────────────────────────

class TestReliabilityConfig:
    """Test the reliability system."""

    def test_config_singleton(self):
        from jarvis.core.reliability import config, ReliabilityConfig
        assert isinstance(config, ReliabilityConfig)

    def test_config_defaults(self):
        from jarvis.core.reliability import config
        assert hasattr(config, "browser_timeout")
        assert hasattr(config, "max_retries")
        assert config.browser_timeout > 0
        assert config.max_retries > 0

    def test_config_update(self):
        from jarvis.core.reliability import config
        old_timeout = config.browser_timeout
        config.browser_timeout = 99
        assert config.browser_timeout == 99
        config.browser_timeout = old_timeout

    def test_config_dataclass(self):
        from jarvis.core.reliability import ReliabilityConfig
        cfg = ReliabilityConfig(llm_timeout=10.0)
        assert cfg.llm_timeout == 10.0
        assert cfg.browser_timeout == 30.0


# ── Workspace Model ─────────────────────────────────────────────────

class TestUnifiedWorkspace:
    """Test the unified Workspace model (Phase 2)."""

    def test_workspace_import(self):
        from jarvis.core.models import Workspace
        assert Workspace is not None

    def test_workspace_create(self):
        from jarvis.core.models import Workspace
        ws = Workspace(goal="Test mission", owner="user")
        assert ws.goal == "Test mission"
        assert ws.owner == "user"

    def test_workspace_to_dict(self):
        from jarvis.core.models import Workspace
        ws = Workspace(goal="Test", owner="user")
        d = ws.dict()
        assert isinstance(d, dict)
        assert d["goal"] == "Test"
        assert "created_at" in d
        assert "id" in d

    def test_workspace_has_core_fields(self):
        from jarvis.core.models import Workspace
        ws = Workspace(goal="Test", owner="user")
        assert hasattr(ws, "goal")
        assert hasattr(ws, "owner")
        assert hasattr(ws, "status")
        assert hasattr(ws, "tasks")
        assert hasattr(ws, "timeline_events")
        assert hasattr(ws, "research_findings")
        assert hasattr(ws, "verification_results")
        assert hasattr(ws, "errors")


# ── Event Bus Collaboration ────────────────────────────────────────

class TestEventBusCollaboration:
    """Test cross-agent event bus (worker collaboration)."""

    def test_event_bus_import(self):
        from jarvis.core.events import EventBus
        eb = EventBus()
        assert eb is not None

    def test_event_bus_emit_subscribe(self):
        from jarvis.core.events import EventBus, Event
        eb = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        loop.run_until_complete(eb.on("test.event", handler))
        loop.run_until_complete(eb.emit(Event(type="test.event", data={"msg": "hello"})))
        assert len(received) == 1
        assert received[0].data["msg"] == "hello"


# ── Rate Limiting ───────────────────────────────────────────────────

class TestRateLimiting:
    """Test API rate limiting."""

    def test_rate_limiter_import(self):
        from jarvis.web.rate_limit import RateLimiter
        rl = RateLimiter()
        assert rl is not None

    def test_rate_limiter_allows_within_limit(self):
        from jarvis.web.rate_limit import RateLimiter
        rl = RateLimiter()
        for _ in range(4):
            assert rl.is_allowed("test_key", max_requests=5, window_seconds=60) is True

    def test_rate_limiter_blocks_over_limit(self):
        from jarvis.web.rate_limit import RateLimiter
        rl = RateLimiter()
        for _ in range(5):
            rl.is_allowed("test_key2", max_requests=5, window_seconds=60)
        assert rl.is_allowed("test_key2", max_requests=5, window_seconds=60) is False


# ── Old Tool Registry (backward compat) ────────────────────────────

class TestOldToolRegistry:
    """Ensure the old ToolRegistry still works (backward compat)."""

    def test_import_models(self):
        from jarvis.tools.models import ToolCapability, ToolInfo, ToolCategory
        assert ToolCapability is not None
        assert ToolInfo is not None
        assert ToolCategory is not None

    def test_tool_category_enum(self):
        from jarvis.tools.models import ToolCategory
        assert ToolCategory.CAD.value == "cad"
        assert ToolCategory.PCB.value == "pcb"
        assert ToolCategory.TESTING.value == "testing"

    def test_tool_capability(self):
        from jarvis.tools.models import ToolCapability
        c = ToolCapability(name="branching", description="Create branches")
        d = c.to_dict()
        assert d["name"] == "branching"

    def test_tool_info(self):
        from jarvis.tools.models import ToolInfo
        t = ToolInfo(name="pytest", category="testing", available=True)
        d = t.to_dict()
        assert d["name"] == "pytest"
        assert d["available"] is True
