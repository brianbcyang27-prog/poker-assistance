"""Tests for JARVIS Plugin system (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.plugins import PluginManager, Plugin, PluginManifest, PluginType


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestPluginModels:
    def test_plugin_type(self):
        assert PluginType.TOOL.value == "tool"
        assert PluginType.WORKER.value == "worker"
        assert PluginType.LLM_PROVIDER.value == "llm_provider"

    def test_create_plugin(self):
        plugin = Plugin(name="test-plugin", version="1.0.0", author="Test")
        assert plugin.name == "test-plugin"
        assert plugin.version == "1.0.0"
        assert plugin.enabled is True
        assert plugin.loaded_at is None

    def test_create_manifest(self):
        manifest = PluginManifest(
            name="my-plugin", version="0.1.0", author="Me",
            description="A test plugin", plugin_type=PluginType.TOOL,
        )
        assert manifest.name == "my-plugin"
        assert manifest.plugin_type == PluginType.TOOL
        assert manifest.entry_point == "__init__.py"

    def test_manifest_from_dict(self):
        data = {
            "name": "dict-plugin",
            "version": "2.0.0",
            "author": "Dict",
            "description": "From dict",
            "plugin_type": "worker",
            "entry_point": "main.py",
            "dependencies": ["requests"],
        }
        manifest = PluginManifest.from_dict(data)
        assert manifest.name == "dict-plugin"
        assert manifest.plugin_type == PluginType.WORKER
        assert manifest.entry_point == "main.py"
        assert "requests" in manifest.dependencies

    def test_manifest_from_dict_unknown_type(self):
        data = {"name": "x", "plugin_type": "unknown_type"}
        manifest = PluginManifest.from_dict(data)
        assert manifest.plugin_type == PluginType.TOOL

    def test_manifest_to_dict(self):
        manifest = PluginManifest(name="a", version="1.0", plugin_type=PluginType.KING)
        d = manifest.to_dict()
        assert d["name"] == "a"
        assert d["plugin_type"] == "king"


# ════════════════════════════════════════════════════════════
# Manager Tests
# ════════════════════════════════════════════════════════════

class TestPluginManager:
    def setup_method(self):
        self.manager = PluginManager()

    def test_discover_no_plugins(self):
        plugins = _run(self.manager.discover(["/nonexistent/path"]))
        assert plugins == []

    def test_list_plugins_empty(self):
        plugins = _run(self.manager.list_plugins())
        assert plugins == []

    def test_get_plugin_none(self):
        plugin = _run(self.manager.get_plugin("nonexistent"))
        assert plugin is None

    def test_discover_with_empty_dirs(self):
        plugins = _run(self.manager.discover([]))
        assert plugins == []

    def test_discover_nonexistent_dir(self):
        plugins = _run(self.manager.discover(["/no/such/dir"]))
        assert plugins == []

    def test_manager_start_empty(self):
        assert len(self.manager._plugins) == 0
        assert len(self.manager._modules) == 0
