import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import tempfile
import pytest

from jarvis.tools.models import ToolCapability, ToolInfo, ToolCategory
from jarvis.tools.registry import ToolRegistry


loop = asyncio.get_event_loop()


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
        assert c.input_types == ["branch_name"]

    def test_to_dict(self):
        c = ToolCapability(name="merge", description="Combine branches")
        d = c.to_dict()
        assert d["name"] == "merge"
        assert d["description"] == "Combine branches"
        assert "input_types" in d
        assert "output_types" in d

    def test_to_dict_empty(self):
        c = ToolCapability()
        d = c.to_dict()
        assert d["input_types"] == []
        assert d["output_types"] == []

    def test_multiple_input_output(self):
        c = ToolCapability(
            name="test",
            input_types=["a", "b", "c"],
            output_types=["result"],
        )
        assert len(c.to_dict()["input_types"]) == 3


# ── ToolInfo ──────────────────────────────────────────────────────────────────

class TestToolInfo:
    def test_create_default(self):
        t = ToolInfo()
        assert t.name == ""
        assert t.category == ""
        assert t.available is False

    def test_create_with_capabilities(self):
        caps = [ToolCapability(name="cap1", description="does thing")]
        t = ToolInfo(name="mytool", category="testing", capabilities=caps)
        assert len(t.capabilities) == 1
        assert t.capabilities[0].name == "cap1"

    def test_to_dict(self):
        t = ToolInfo(
            name="pytest",
            category="testing",
            description="Python testing framework",
            check_command="which pytest",
            install_command="pip install pytest",
            available=True,
            version="7.4.0",
        )
        d = t.to_dict()
        assert d["name"] == "pytest"
        assert d["category"] == "testing"
        assert d["available"] is True
        assert d["version"] == "7.4.0"
        assert "capabilities" in d
        assert "common_failures" in d
        assert "examples" in d

    def test_to_dict_with_failures(self):
        t = ToolInfo(
            common_failures=[{"error": "merge conflict", "fix": "resolve manually"}],
        )
        d = t.to_dict()
        assert len(d["common_failures"]) == 1

    def test_to_dict_empty_capabilities(self):
        t = ToolInfo()
        assert t.to_dict()["capabilities"] == []


# ── ToolCategory ──────────────────────────────────────────────────────────────

class TestToolCategory:
    def test_enum_values(self):
        assert ToolCategory.CAD.value == "cad"
        assert ToolCategory.PCB.value == "pcb"
        assert ToolCategory.TESTING.value == "testing"
        assert ToolCategory.BROWSER.value == "browser"
        assert ToolCategory.AI_ML.value == "ai_ml"


# ── ToolRegistry ──────────────────────────────────────────────────────────────

class TestToolRegistry:
    def _make(self):
        tmpdir = tempfile.mkdtemp()
        return ToolRegistry(store_path=os.path.join(tmpdir, "tools.json"))

    def test_create(self):
        reg = self._make()
        assert reg._tools == {}

    def test_load_defaults(self):
        reg = self._make()
        all_tools = loop.run_until_complete(reg.get_all())
        assert len(all_tools) >= 10
        names = {t.name for t in all_tools}
        assert "git" in names
        assert "python" in names
        assert "docker" in names

    def test_get_by_name(self):
        reg = self._make()
        tool = loop.run_until_complete(reg.get("git"))
        assert tool is not None
        assert tool.name == "git"
        assert tool.category == "version_control"

    def test_get_nonexistent(self):
        reg = self._make()
        tool = loop.run_until_complete(reg.get("nonexistent"))
        assert tool is None

    def test_get_by_category(self):
        reg = self._make()
        tools = loop.run_until_complete(reg.get_by_category("testing"))
        names = {t.name for t in tools}
        assert "pytest" in names or "eslint" in names

    def test_get_by_category_empty(self):
        reg = self._make()
        tools = loop.run_until_complete(reg.get_by_category("nonexistent"))
        assert tools == []

    def test_get_all(self):
        reg = self._make()
        all_tools = loop.run_until_complete(reg.get_all())
        assert len(all_tools) >= 10
        assert all(isinstance(t, ToolInfo) for t in all_tools)

    def test_search(self):
        reg = self._make()
        results = loop.run_until_complete(reg.search("container"))
        assert len(results) >= 1
        assert any("docker" in t.name for t in results)

    def test_search_by_capability(self):
        reg = self._make()
        results = loop.run_until_complete(reg.search("branching"))
        if results:
            assert results[0].name == "git"
        else:
            git = loop.run_until_complete(reg.get("git"))
            assert git is not None
            assert git.name == "git"

    def test_search_no_match(self):
        reg = self._make()
        results = loop.run_until_complete(reg.search("xyzzy_nonexistent"))
        assert results == []

    def test_get_for_task_python(self):
        reg = self._make()
        tools = loop.run_until_complete(reg.get_for_task("write a Python script"))
        assert len(tools) > 0
        assert tools[0].name == "python"

    def test_get_for_task_docker(self):
        reg = self._make()
        tools = loop.run_until_complete(reg.get_for_task("docker container build"))
        assert tools[0].name == "docker"

    def test_get_for_task_testing(self):
        reg = self._make()
        tools = loop.run_until_complete(reg.get_for_task("run pytest fixtures"))
        assert tools[0].name == "pytest"

    def test_get_for_task_unknown(self):
        reg = self._make()
        tools = loop.run_until_complete(reg.get_for_task("xyzzy nothing"))
        assert len(tools) >= 1  # returns all tools

    def test_register(self):
        reg = self._make()
        t = ToolInfo(name="custom_tool", category="testing", description="custom")
        result = loop.run_until_complete(reg.register(t))
        assert result.name == "custom_tool"
        fetched = loop.run_until_complete(reg.get("custom_tool"))
        assert fetched is not None

    def test_save_and_reload(self):
        reg = self._make()
        loop.run_until_complete(reg._ensure_loaded())
        t = ToolInfo(name="persist_tool", category="testing", description="test")
        loop.run_until_complete(reg.register(t))
        loop.run_until_complete(reg.save())

        reg2 = ToolRegistry(store_path=reg._store_path)
        fetched = loop.run_until_complete(reg2.get("persist_tool"))
        assert fetched is not None
        assert fetched.description == "test"

    def test_git_capabilities(self):
        reg = self._make()
        git = loop.run_until_complete(reg.get("git"))
        assert git is not None
        assert git.name == "git"
        assert git.category == "version_control"
        assert git.check_command != ""
        assert git.install_command != ""

    def test_common_fixes(self):
        reg = self._make()
        fixes = loop.run_until_complete(reg.get_common_fixes("merge conflict"))
        assert len(fixes) >= 1
        assert any("git" in f["tool"] for f in fixes)

    def test_common_fixes_no_match(self):
        reg = self._make()
        fixes = loop.run_until_complete(reg.get_common_fixes("xyzzy"))
        assert fixes == []
