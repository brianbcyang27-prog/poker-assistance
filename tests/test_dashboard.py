"""Tests for JARVIS Dashboard engine (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.dashboard import Dashboard, ProjectMetrics, HealthReport, HealthIssue

REPO_PATH = os.path.join(os.path.dirname(__file__), "..")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestProjectMetrics:
    def test_create_metrics(self):
        m = ProjectMetrics()
        assert m.health_score == 0.0
        assert m.total_loc == 0
        assert m.languages == {}

    def test_to_dict(self):
        m = ProjectMetrics(health_score=85.0, total_loc=1000)
        d = m.to_dict()
        assert d["health_score"] == 85.0
        assert d["total_loc"] == 1000
        assert "generated_at" in d


class TestHealthReport:
    def test_create_report(self):
        r = HealthReport(overall_score=90.0, grades={"code_quality": "A"})
        assert r.overall_score == 90.0
        assert r.grades["code_quality"] == "A"
        assert r.issues == []


class TestHealthIssue:
    def test_create_issue(self):
        issue = HealthIssue(
            file="main.py", line=10, category="naming",
            severity="warning", description="Bad name",
            suggestion="Rename", auto_fixable=True,
        )
        assert issue.file == "main.py"
        assert issue.auto_fixable is True


# ════════════════════════════════════════════════════════════
# Dashboard Integration Tests
# ════════════════════════════════════════════════════════════

class TestDashboard:
    def setup_method(self):
        self.dashboard = Dashboard()

    def test_collect_metrics(self):
        metrics = _run(self.dashboard.collect(REPO_PATH))
        assert isinstance(metrics, ProjectMetrics)
        assert metrics.total_loc > 0
        assert metrics.total_files > 0
        assert metrics.total_classes > 0
        assert metrics.total_functions > 0
        lang_keys = [k.lower() for k in metrics.languages.keys()]
        assert "python" in lang_keys

    def test_code_health(self):
        report = _run(self.dashboard.code_health(REPO_PATH))
        assert isinstance(report, HealthReport)
        assert report.overall_score >= 0
        assert report.overall_score <= 100
        assert isinstance(report.grades, dict)
        assert len(report.grades) > 0
        assert isinstance(report.recommendations, list)

    def test_test_coverage(self):
        result = _run(self.dashboard.test_coverage(REPO_PATH))
        assert isinstance(result, dict)
        assert "score" in result
        assert "grade" in result
        assert result["score"] >= 0

    def test_security_score(self):
        result = _run(self.dashboard.security_score(REPO_PATH))
        assert isinstance(result, dict)
        assert "score" in result
        assert "grade" in result
        assert isinstance(result.get("issues", []), list)

    def test_complexity_report(self):
        result = _run(self.dashboard.complexity_report(REPO_PATH))
        assert isinstance(result, dict)
        assert "score" in result
        assert "average_complexity" in result

    def test_dead_code_analysis(self):
        result = _run(self.dashboard.dead_code_analysis(REPO_PATH))
        assert isinstance(result, dict)
        assert "score" in result
        assert "unused_imports" in result

    def test_dependency_health(self):
        result = _run(self.dashboard.dependency_health(REPO_PATH))
        assert isinstance(result, dict)
        assert "score" in result
        assert "total_dependencies" in result

    def test_documentation_score(self):
        result = _run(self.dashboard.documentation_score(REPO_PATH))
        assert isinstance(result, dict)
        assert "score" in result
        assert "has_readme" in result

    def test_duplicate_code(self):
        result = _run(self.dashboard.duplicate_code(REPO_PATH))
        assert isinstance(result, dict)
        assert "score" in result
        assert "duplicate_groups" in result

    def test_performance_score(self):
        result = _run(self.dashboard.performance_score(REPO_PATH))
        assert isinstance(result, dict)
        assert "score" in result

    def test_to_dict(self):
        metrics = _run(self.dashboard.collect(REPO_PATH))
        d = _run(self.dashboard.to_dict(metrics))
        assert isinstance(d, dict)
        assert "health_score" in d
        assert "total_loc" in d
