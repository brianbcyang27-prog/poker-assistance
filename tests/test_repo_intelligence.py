"""Tests for JARVIS Repository Intelligence engine (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.repo_intelligence import (
    RepoIntelligence,
    ProjectDNA,
    DependencyGraph,
    DependencyNode,
    DependencyEdge,
    ArchitectureReport,
    CodeStyleReport,
    DebtReport,
    DebtIssue,
    ImprovementReport,
    ImprovementItem,
)

REPO_PATH = os.path.join(os.path.dirname(__file__), "..")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestProjectDNA:
    def test_create_project_dna(self):
        dna = ProjectDNA(name="test-project", purpose="Testing")
        assert dna.name == "test-project"
        assert dna.purpose == "Testing"
        assert dna.languages == {}
        assert dna.frameworks == []
        assert dna.health_score == 0.0

    def test_project_dna_fields(self):
        dna = ProjectDNA(
            name="myapp",
            languages={"python": 80.0, "javascript": 20.0},
            frameworks=["fastapi", "pytest"],
            build_system={"pyproject.toml": "poetry"},
            architecture_style="modular",
            health_score=85.5,
            debt_score=12.3,
        )
        assert dna.languages["python"] == 80.0
        assert "fastapi" in dna.frameworks
        assert dna.architecture_style == "modular"
        assert dna.health_score == 85.5


class TestDependencyModels:
    def test_dependency_node(self):
        node = DependencyNode(name="requests", version="2.28.0", type="direct", ecosystem="pypi")
        assert node.name == "requests"
        assert node.ecosystem == "pypi"

    def test_dependency_edge(self):
        edge = DependencyEdge(source="app", target="requests", type="requires")
        assert edge.source == "app"
        assert edge.type == "requires"

    def test_dependency_graph(self):
        graph = DependencyGraph()
        graph.nodes.append(DependencyNode(name="a", version="1.0", type="direct", ecosystem="pypi"))
        graph.edges.append(DependencyEdge(source="a", target="b", type="requires"))
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 1


class TestArchitectureReport:
    def test_create_report(self):
        report = ArchitectureReport(style="modular", modules=["core", "web"])
        assert report.style == "modular"
        assert len(report.modules) == 2
        assert report.patterns == []


class TestCodeStyleReport:
    def test_defaults(self):
        report = CodeStyleReport()
        assert report.avg_line_length == 0.0
        assert report.naming_convention == "unknown"


class TestDebtModels:
    def test_debt_issue(self):
        issue = DebtIssue(
            file="main.py", line=10, category="complexity",
            description="Too long", severity="high", suggestion="Refactor",
        )
        assert issue.file == "main.py"
        assert issue.severity == "high"

    def test_debt_report(self):
        report = DebtReport(score=35.0, summary="Some debt")
        assert report.score == 35.0
        assert report.issues == []


# ════════════════════════════════════════════════════════════
# Analyzer Tests (against the jarvis repo itself)
# ════════════════════════════════════════════════════════════

class TestRepoIntelligence:
    def setup_method(self):
        self.ri = RepoIntelligence()

    def test_detect_languages(self):
        langs = _run(self.ri.detect_languages(REPO_PATH))
        assert isinstance(langs, dict)
        assert len(langs) > 0
        assert "python" in langs
        assert langs["python"] > 50

    def test_detect_frameworks(self):
        frameworks = _run(self.ri.detect_frameworks(REPO_PATH))
        assert isinstance(frameworks, list)
        assert isinstance(frameworks, list)

    def test_detect_build_system(self):
        build = _run(self.ri.detect_build_system(REPO_PATH))
        assert isinstance(build, dict)
        assert len(build) > 0

    def test_analyze_dependencies(self):
        graph = _run(self.ri.analyze_dependencies(REPO_PATH))
        assert isinstance(graph, DependencyGraph)
        assert isinstance(graph.nodes, list)

    def test_analyze_architecture(self):
        report = _run(self.ri.analyze_architecture(REPO_PATH))
        assert isinstance(report, ArchitectureReport)
        assert report.style != ""
        assert isinstance(report.modules, list)

    def test_analyze_code_style(self):
        style = _run(self.ri.analyze_code_style(REPO_PATH))
        assert isinstance(style, CodeStyleReport)
        assert style.avg_line_length > 0
        assert style.naming_convention in ("snake_case", "camelCase", "mixed")

    def test_analyze_debt(self):
        debt = _run(self.ri.analyze_debt(REPO_PATH))
        assert isinstance(debt, DebtReport)
        assert debt.score >= 0
        assert isinstance(debt.issues, list)

    def test_generate_dna(self):
        dna = _run(self.ri.generate_dna(REPO_PATH))
        assert isinstance(dna, ProjectDNA)
        assert dna.name == "jarvis"
        assert "python" in dna.languages
        assert dna.languages["python"] > 50
        assert dna.architecture_style != ""
        assert dna.health_score >= 0
        assert dna.risk_score >= 0

    def test_analyze_full(self):
        dna = _run(self.ri.analyze(REPO_PATH))
        assert isinstance(dna, ProjectDNA)
        assert dna.name == "jarvis"
