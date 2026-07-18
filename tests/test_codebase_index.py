"""Tests for JARVIS Codebase Index engine (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.codebase_index import (
    CodebaseIndex,
    Symbol,
    SearchResult,
    FileIndex,
    RepoIndex,
    SearchEngine,
)

REPO_PATH = os.path.join(os.path.dirname(__file__), "..")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestSymbolModel:
    def test_create_symbol(self):
        sym = Symbol(name="MissionPipeline", kind="class", file_path="test.py", line_start=1, line_end=50)
        assert sym.name == "MissionPipeline"
        assert sym.kind == "class"
        assert sym.full_name == "MissionPipeline"

    def test_symbol_with_parent(self):
        sym = Symbol(name="run", kind="method", file_path="test.py", line_start=1, parent_class="Pipeline")
        assert sym.full_name == "Pipeline.run"

    def test_symbol_to_dict(self):
        sym = Symbol(name="foo", kind="function", file_path="a.py", line_start=10)
        d = sym.to_dict()
        assert d["name"] == "foo"
        assert d["kind"] == "function"
        assert d["line_start"] == 10

    def test_symbol_from_dict(self):
        data = {"name": "bar", "kind": "variable", "file_path": "b.py", "line_start": 5}
        sym = Symbol.from_dict(data)
        assert sym.name == "bar"
        assert sym.kind == "variable"

    def test_symbol_defaults(self):
        sym = Symbol(name="x", kind="variable", file_path="c.py", line_start=1)
        assert sym.line_end == 1
        assert sym.complexity == 1
        assert sym.metadata == {}


class TestFileIndex:
    def test_create_file_index(self):
        fi = FileIndex(path="main.py", language="python")
        assert fi.path == "main.py"
        assert fi.loc == 0
        assert fi.symbols == []

    def test_to_dict_and_back(self):
        fi = FileIndex(path="test.py", language="python", loc=100)
        d = fi.to_dict()
        fi2 = FileIndex.from_dict(d)
        assert fi2.path == "test.py"
        assert fi2.loc == 100


class TestRepoIndex:
    def test_repo_index_defaults(self):
        ri = RepoIndex()
        assert ri.files == {}
        assert ri.stats == {}


# ════════════════════════════════════════════════════════════
# Integration Tests (against jarvis repo)
# ════════════════════════════════════════════════════════════

class TestCodebaseIndex:
    def setup_method(self):
        self.index = CodebaseIndex()
        _run(self.index.index(REPO_PATH))

    def test_index_populated(self):
        stats = _run(self.index.get_repo_stats())
        assert stats["total_files"] > 0
        assert stats["total_symbols"] > 0
        assert stats["total_loc"] > 0

    def test_python_is_dominant(self):
        stats = _run(self.index.get_repo_stats())
        langs = stats.get("languages", {})
        assert "python" in langs
        assert langs["python"] > 0

    def test_search_by_name(self):
        results = _run(self.index.search("MissionPipeline", search_type="name"))
        assert isinstance(results, list)

    def test_search_symbol(self):
        syms = _run(self.index.search_symbol("Mission"))
        assert isinstance(syms, list)

    def test_search_references(self):
        refs = _run(self.index.search_references("Mission"))
        assert isinstance(refs, list)

    def test_get_call_graph(self):
        cg = _run(self.index.get_call_graph("run"))
        assert isinstance(cg, dict)

    def test_get_import_graph(self):
        ig = _run(self.index.get_import_graph("jarvis.cli"))
        assert isinstance(ig, dict)

    def test_get_module_graph(self):
        mg = _run(self.index.get_module_graph())
        assert isinstance(mg, dict)
        assert len(mg) > 0

    def test_get_repo_stats(self):
        stats = _run(self.index.get_repo_stats())
        assert "total_files" in stats
        assert "total_symbols" in stats
        assert "total_loc" in stats
        assert "languages" in stats

    def test_get_file_stats(self):
        # Find a known file
        for rel_path in self.index.repo_index.files:
            if rel_path.endswith("cli.py"):
                stats = _run(self.index.get_file_stats(rel_path))
                assert stats["language"] == "python"
                assert stats["loc"] > 0
                break

    def test_search_docstring(self):
        results = _run(self.index.search("pipeline", search_type="docstring"))
        assert isinstance(results, list)

    def test_search_signature(self):
        results = _run(self.index.search("async", search_type="signature"))
        assert isinstance(results, list)

    def test_get_inheritance_graph(self):
        ig = _run(self.index.get_inheritance_graph("BaseWorker"))
        assert isinstance(ig, dict)
