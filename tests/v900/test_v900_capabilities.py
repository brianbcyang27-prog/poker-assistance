"""v9.0.0 regression tests — capability metadata and structure."""


class TestCapabilityMetadata:
    """Capability dataclass has all required fields."""

    def test_capability_required_fields(self):
        from jarvis.core.capabilities import Capability, CapType

        cap = Capability(name="test", owner="♠K", type=CapType.TOOL)
        assert cap.name == "test"
        assert cap.owner == "♠K"
        assert cap.type == CapType.TOOL

    def test_capability_defaults(self):
        from jarvis.core.capabilities import Capability, CapType

        cap = Capability(name="defaults", owner="test", type=CapType.WORKER)
        assert cap.description == ""
        assert cap.version == "1.0.0"
        assert cap.enabled is True
        assert cap.total_calls == 0
        assert cap.total_failures == 0
        assert cap.success_rate == 1.0
        assert cap.required_permissions == []

    def test_capability_to_dict(self):
        from jarvis.core.capabilities import Capability, CapType

        cap = Capability(name="dict_test", owner="♠K", type=CapType.TOOL, description="test")
        d = cap.to_dict()
        assert d["name"] == "dict_test"
        assert d["owner"] == "♠K"
        assert d["type"] == "tool"
        assert d["description"] == "test"
        assert d["version"] == "1.0.0"
        assert d["enabled"] is True

    def test_capability_from_dict(self):
        from jarvis.core.capabilities import Capability, CapType

        d = {"name": "from_dict", "owner": "♥Q", "type": "skill", "description": "loaded"}
        cap = Capability.from_dict(d)
        assert cap.name == "from_dict"
        assert cap.owner == "♥Q"
        assert cap.type == CapType.SKILL
        assert cap.description == "loaded"


class TestCapTypeEnum:
    """CapType enum has all expected values."""

    def test_cap_type_values(self):
        from jarvis.core.capabilities import CapType

        assert CapType.TOOL.value == "tool"
        assert CapType.WORKER.value == "worker"
        assert CapType.ACTION.value == "action"
        assert CapType.SKILL.value == "skill"
        assert CapType.MEMORY.value == "memory"

    def test_cap_type_valid_types(self):
        from jarvis.core.capabilities import CapType

        types = {t.value for t in CapType}
        assert types == {"tool", "worker", "action", "skill", "memory"}
