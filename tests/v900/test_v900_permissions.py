"""v9.0.0 regression tests — capability registry operations."""

import pytest


class TestCapabilityRegistry:
    """Capability registry CRUD and query operations."""

    @pytest.fixture
    def reg(self):
        from jarvis.core.capabilities import Capability, CapabilityRegistry, CapType

        registry = CapabilityRegistry()
        return registry, Capability, CapType

    @pytest.mark.asyncio
    async def test_register(self, reg):
        registry, Cap, CapType = reg
        result = await registry.register(
            Cap(
                name="test_cap",
                owner="test",
                type=CapType.TOOL,
                description="A test capability",
            )
        )
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_get(self, reg):
        registry, Cap, CapType = reg
        await registry.register(Cap(name="test_get", owner="test", type=CapType.TOOL))
        cap = await registry.get("test_get")
        assert cap is not None
        assert cap.name == "test_get"

    @pytest.mark.asyncio
    async def test_get_missing(self, reg):
        registry, Cap, CapType = reg
        cap = await registry.get("nonexistent")
        assert cap is None

    @pytest.mark.asyncio
    async def test_unregister(self, reg):
        registry, Cap, CapType = reg
        await registry.register(Cap(name="test_unreg", owner="test", type=CapType.TOOL))
        result = await registry.unregister("test_unreg")
        assert result["ok"] is True
        assert await registry.get("test_unreg") is None

    @pytest.mark.asyncio
    async def test_unregister_missing(self, reg):
        registry, Cap, CapType = reg
        result = await registry.unregister("nonexistent")
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_query_by_type(self, reg):
        registry, Cap, CapType = reg
        await registry.register(Cap(name="tool1", owner="a", type=CapType.TOOL))
        await registry.register(Cap(name="tool2", owner="a", type=CapType.TOOL))
        await registry.register(Cap(name="skill1", owner="a", type=CapType.SKILL))
        tools = await registry.query(type=CapType.TOOL)
        assert len(tools) == 2
        skills = await registry.query(type=CapType.SKILL)
        assert len(skills) == 1

    @pytest.mark.asyncio
    async def test_query_by_owner(self, reg):
        registry, Cap, CapType = reg
        await registry.register(Cap(name="a1", owner="king_a", type=CapType.TOOL))
        await registry.register(Cap(name="b1", owner="king_b", type=CapType.TOOL))
        king_a_caps = await registry.query(owner="king_a")
        assert len(king_a_caps) == 1

    @pytest.mark.asyncio
    async def test_record_call(self, reg):
        registry, Cap, CapType = reg
        await registry.register(Cap(name="tracked", owner="test", type=CapType.TOOL))
        await registry.record_call("tracked", success=True, latency_ms=100)
        cap = await registry.get("tracked")
        assert cap.total_calls == 1
        assert cap.total_failures == 0

    @pytest.mark.asyncio
    async def test_record_call_failure(self, reg):
        registry, Cap, CapType = reg
        await registry.register(Cap(name="tracked_fail", owner="test", type=CapType.TOOL))
        await registry.record_call("tracked_fail", success=False)
        cap = await registry.get("tracked_fail")
        assert cap.total_calls == 1
        assert cap.total_failures == 1
        assert cap.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_get_all(self, reg):
        registry, Cap, CapType = reg
        await registry.register(Cap(name="cap1", owner="a", type=CapType.TOOL))
        await registry.register(Cap(name="cap2", owner="b", type=CapType.WORKER))
        all_caps = await registry.get_all()
        assert len(all_caps) == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, reg):
        registry, Cap, CapType = reg
        await registry.register(Cap(name="stat1", owner="a", type=CapType.TOOL))
        stats = await registry.get_stats()
        assert stats["total"] >= 1

    @pytest.mark.asyncio
    async def test_find_best_by_description(self, reg):
        registry, Cap, CapType = reg
        await registry.register(
            Cap(
                name="web_search",
                owner="a",
                type=CapType.TOOL,
                description="Search the web for information",
                success_rate=0.9,
                latency_ms=200,
                cost=0.0,
            )
        )
        best = await registry.find_best(type=CapType.TOOL, description="search web")
        assert best is not None
        assert best.name == "web_search"

    @pytest.mark.asyncio
    async def test_generate_capability_prompt(self, reg):
        registry, Cap, CapType = reg
        await registry.register(
            Cap(
                name="test_prompt",
                owner="a",
                type=CapType.TOOL,
                description="Test capability",
                category="testing",
            )
        )
        prompt = await registry.generate_capability_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "test_prompt" in prompt
