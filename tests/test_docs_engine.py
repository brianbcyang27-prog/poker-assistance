"""Tests for JARVIS Documentation Engine (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.docs_engine import DocsEngine, ModuleDoc, ProjectDocs

REPO_PATH = os.path.join(os.path.dirname(__file__), "..")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestModuleDoc:
    def test_create_module_doc(self):
        doc = ModuleDoc(
            name="jarvis.cli",
            purpose="CLI interface",
            architecture="Module-level code",
            public_api=["jarvis.cli.main"],
            examples=[],
            dependencies=["argparse"],
            limitations=[],
            future_work=[],
        )
        assert doc.name == "jarvis.cli"
        assert len(doc.public_api) == 1

    def test_module_doc_defaults(self):
        doc = ModuleDoc(
            name="test", purpose="test", architecture="test",
            public_api=[], examples=[], dependencies=[],
            limitations=[], future_work=[],
        )
        assert doc.examples == []


class TestProjectDocs:
    def test_create_project_docs(self):
        pd = ProjectDocs(
            modules=[], api_reference="# API", architecture_book="# Arch",
            handbook="# Handbook", database_docs="", readme="# README",
        )
        assert pd.api_reference == "# API"
        assert pd.readme == "# README"


# ════════════════════════════════════════════════════════════
# Engine Tests (against jarvis repo)
# ════════════════════════════════════════════════════════════

class TestDocsEngine:
    def setup_method(self):
        self.engine = DocsEngine()

    def test_generate_module_docs(self):
        modules = _run(self.engine.generate_module_docs(REPO_PATH))
        assert isinstance(modules, list)
        assert len(modules) > 0
        for mod in modules:
            assert isinstance(mod, ModuleDoc)
            assert mod.name != ""
            assert mod.purpose != ""

    def test_generate_api_reference(self):
        api_ref = _run(self.engine.generate_api_reference(REPO_PATH))
        assert isinstance(api_ref, str)
        assert "# API Reference" in api_ref
        assert len(api_ref) > 100

    def test_generate_architecture_book(self):
        arch = _run(self.engine.generate_architecture_book(REPO_PATH))
        assert isinstance(arch, str)
        assert "# Architecture Overview" in arch
        assert "Module Map" in arch

    def test_generate_developer_handbook(self):
        handbook = _run(self.engine.generate_developer_handbook(REPO_PATH))
        assert isinstance(handbook, str)
        assert "Developer Handbook" in handbook
        assert "Getting Started" in handbook
        assert "Coding Conventions" in handbook

    def test_generate_readme(self):
        readme = _run(self.engine.generate_readme(REPO_PATH))
        assert isinstance(readme, str)
        assert "# jarvis" in readme
        assert "Overview" in readme
        assert "Modules" in readme
        assert "Installation" in readme

    def test_generate_database_docs(self):
        db_docs = _run(self.engine.generate_database_docs(REPO_PATH))
        assert isinstance(db_docs, str)
        assert "# Database Schema" in db_docs

    def test_generate_full_docs(self):
        docs = _run(self.engine.generate_full_docs(REPO_PATH))
        assert isinstance(docs, ProjectDocs)
        assert len(docs.modules) > 0
        assert "# API Reference" in docs.api_reference
        assert "# Architecture Overview" in docs.architecture_book
        assert "Developer Handbook" in docs.handbook
        assert "# jarvis" in docs.readme

    def test_module_docs_have_api(self):
        modules = _run(self.engine.generate_module_docs(REPO_PATH))
        documented = [m for m in modules if m.public_api]
        assert len(documented) > 0
