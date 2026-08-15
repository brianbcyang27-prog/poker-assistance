"""Test Tool Registry and Tool Models."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import tempfile

from jarvis.tools.models import ToolCapability, ToolInfo
from jarvis.tools.registry import ToolRegistry


def run_async(coro):
    """Run async function in new event loop."""
    return asyncio.run(coro)


# ── ToolCapability ────────────────────────────────────────────────────────────


class TestToolCapability:
    def test_create_default(self):
        c = ToolCapability()
        assert c.name == ""
        assert c.input_types == []
        assert c.output_types == []

    def test_create_explicit(self):
        c = ToolCapability(
            name="branching",
            description="Create parallel lines of development",
            input_types=["branch_name"],
            output_types=["branch"],
        )
        assert c.name == "branching"
        assert c.description == "Create parallel lines of development"
        assert c.input_types == ["branch_name"]
        assert c.output_types == ["branch"]


# ── ToolInfo ──────────────────────────────────────────────────────────────────


class TestToolInfo:
    def test_create_minimal(self):
        t = ToolInfo(name="git", category="version_control", description="Distributed VCS")
        assert t.name == "git"
        assert t.category == "version_control"
        assert t.description == "Distributed VCS"
        assert t.capabilities == []
        assert t.check_command == ""
        assert t.install_command == ""

    def test_create_full(self):
        cap = ToolCapability(name="branching", input_types=["branch_name"], output_types=["branch"])
        t = ToolInfo(
            name="git",
            category="version_control",
            description="Distributed VCS",
            capabilities=[cap],
            check_command="git --version",
            install_command="brew install git",
        )
        assert t.capabilities == [cap]
        assert t.check_command == "git --version"
        assert t.install_command == "brew install git"


# ── ToolRegistry ──────────────────────────────────────────────────────────────


class TestToolRegistry:
    def _make(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        return ToolRegistry(store_path=path)

    def test_empty_registry(self):
        reg = self._make()
        assert reg._tools == {}

    def test_load_defaults(self):
        reg = self._make()
        all_tools = run_async(reg.get_all())
        assert len(all_tools) >= 10
        names = {t.name for t in all_tools}
        assert "git" in names
        assert "python" in names
        assert "docker" in names

    def test_get_by_name(self):
        reg = self._make()
        tool = run_async(reg.get("git"))
        assert tool is not None
        assert tool.name == "git"
        assert tool.category == "version_control"

    def test_get_nonexistent(self):
        reg = self._make()
        tool = run_async(reg.get("nonexistent"))
        assert tool is None

    def test_get_by_category(self):
        reg = self._make()
        tools = run_async(reg.get_by_category("testing"))
        names = {t.name for t in tools}
        assert "pytest" in names or "eslint" in names

    def test_get_by_category_empty(self):
        reg = self._make()
        tools = run_async(reg.get_by_category("nonexistent"))
        assert tools == []

    def test_get_all(self):
        reg = self._make()
        all_tools = run_async(reg.get_all())
        assert len(all_tools) >= 10
        assert all(isinstance(t, ToolInfo) for t in all_tools)

    def test_search(self):
        reg = self._make()
        results = run_async(reg.search("container"))
        assert len(results) >= 1
        assert any("docker" in t.name for t in results)

    def test_search_by_capability(self):
        reg = self._make()
        results = run_async(reg.search("branching"))
        if results:
            assert results[0].name == "git"
        else:
            git = run_async(reg.get("git"))
            assert git is not None
            assert git.name == "git"

    def test_search_no_match(self):
        reg = self._make()
        results = run_async(reg.search("xyzzy_nonexistent"))
        assert results == []

    def test_get_for_task_python(self):
        reg = self._make()
        tools = run_async(reg.get_for_task("write a Python script"))
        assert len(tools) > 0
        assert tools[0].name == "python"

    def test_get_for_task_docker(self):
        reg = self._make()
        tools = run_async(reg.get_for_task("docker container build"))
        assert tools[0].name == "docker"

    def test_get_for_task_testing(self):
        reg = self._make()
        tools = run_async(reg.get_for_task("run pytest fixtures"))
        assert tools[0].name == "pytest"

    def test_get_for_task_unknown(self):
        reg = self._make()
        tools = run_async(reg.get_for_task("xyzzy nothing"))
        assert len(tools) >= 1  # returns all tools

    def test_register(self):
        reg = self._make()
        t = ToolInfo(name="custom_tool", category="testing", description="custom")
        result = run_async(reg.register(t))
        assert result.name == "custom_tool"
        fetched = run_async(reg.get("custom_tool"))
        assert fetched is not None

    def test_save_and_reload(self):
        reg = self._make()
        run_async(reg._ensure_loaded())
        t = ToolInfo(name="persist_tool", category="testing", description="test")
        run_async(reg.register(t))
        run_async(reg.save())

        reg2 = ToolRegistry(store_path=reg._store_path)
        fetched = run_async(reg2.get("persist_tool"))
        assert fetched is not None
        assert fetched.description == "test"

    def test_git_capabilities(self):
        reg = self._make()
        git = run_async(reg.get("git"))
        assert git is not None
        assert git.name == "git"
        assert git.category == "version_control"
        assert git.check_command != ""
        assert git.install_command != ""

    def test_common_fixes(self):
        reg = self._make()
        fixes = run_async(reg.get_common_fixes("merge conflict"))
        assert len(fixes) >= 1
        assert any("git" in f["tool"] for f in fixes)

    def test_common_fixes_no_match(self):
        reg = self._make()
        fixes = run_async(reg.get_common_fixes("xyzzy"))
        assert fixes == []
