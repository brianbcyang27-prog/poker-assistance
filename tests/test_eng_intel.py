import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from jarvis.eng_intel.models import (
    DriftIssue,
    EngineeringIssue,
    IssueCategory,
    ProjectHealth,
    Recommendation,
    Severity,
)
from jarvis.eng_intel.engine import (
    ArchitectureDriftDetector,
    ComplexityAnalyzer,
    DeadCodeDetector,
    DocumentationChecker,
    DuplicationDetector,
    MissingTestDetector,
    NamingChecker,
    StaleAPIDetector,
    EngineeringIntelEngine,
)
from jarvis.eng_intel import EngineeringIntel


# ---------------------------------------------------------------------------
# EngIntelModels
# ---------------------------------------------------------------------------


class TestEngIntelModels:
    def test_engineering_issue_creation(self):
        issue = EngineeringIssue(
            id="iss-1",
            timestamp="2025-06-15T10:00:00Z",
            file_path="/tmp/main.py",
            line=10,
            category="naming",
            severity="warning",
            description="Function not snake_case",
            suggestion="Rename to snake_case",
            auto_fixable=True,
            confidence=0.9,
        )
        assert issue.id == "iss-1"
        assert issue.category == "naming"
        assert issue.auto_fixable is True

    def test_engineering_issue_to_dict(self):
        issue = EngineeringIssue(
            id="d1", timestamp="2025-01-01T00:00:00Z",
            file_path="x.py", line=1, category="doc",
            severity="info", description="Missing doc", suggestion="Add doc",
        )
        d = issue.to_dict()
        assert d["id"] == "d1"
        assert d["line"] == 1
        assert d["auto_fixable"] is False

    def test_recommendation_creation(self):
        rec = Recommendation(
            id="r1", category="naming", title="Fix naming",
            description="Use snake_case", impact="medium", effort="low",
            files_affected=["a.py", "b.py"], priority_score=5.5,
        )
        assert rec.priority_score == 5.5
        assert len(rec.files_affected) == 2

    def test_recommendation_to_dict(self):
        rec = Recommendation(
            id="r2", category="test", title="Add tests",
            description="No tests found", impact="high", effort="medium",
        )
        d = rec.to_dict()
        assert d["category"] == "test"
        assert d["effort"] == "medium"

    def test_project_health_creation(self):
        h = ProjectHealth(
            overall_score=85.0,
            grades={"naming": "B", "doc": "A"},
            issues_by_category={"naming": 5},
            trends={"naming": "improving"},
        )
        assert h.overall_score == 85.0
        assert h.grades["naming"] == "B"

    def test_project_health_to_dict(self):
        h = ProjectHealth(overall_score=90.0, grades={"doc": "A"})
        d = h.to_dict()
        assert d["overall_score"] == 90.0
        assert d["grades"]["doc"] == "A"

    def test_drift_issue_creation(self):
        drift = DriftIssue(
            module="jarvis/brain",
            expected_pattern="layer isolation",
            actual_pattern="brain imports agents",
            description="Avoid cross-layer imports",
            severity="critical",
        )
        assert drift.severity == "critical"

    def test_drift_issue_to_dict(self):
        drift = DriftIssue(
            module="m", expected_pattern="e", actual_pattern="a",
            description="d", severity="warning",
        )
        d = drift.to_dict()
        assert d["module"] == "m"
        assert d["severity"] == "warning"

    def test_issue_category_values(self):
        assert IssueCategory.DUPLICATION.value == "duplication"
        assert IssueCategory.NAMING.value == "naming"
        assert IssueCategory.DOCUMENTATION.value == "documentation"
        assert IssueCategory.COMPLEXITY.value == "complexity"
        assert IssueCategory.DEAD_CODE.value == "dead_code"
        assert IssueCategory.MISSING_TEST.value == "missing_test"

    def test_severity_values(self):
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.CRITICAL.value == "critical"


# ---------------------------------------------------------------------------
# EngineeringIntel (high-level API)
# ---------------------------------------------------------------------------


class TestEngineeringIntel:
    @pytest.fixture
    def intel(self):
        return EngineeringIntel()

    @pytest.fixture
    def sample_python_file(self, tmp_path):
        content = '''
"""Sample module for testing."""

import os
import json

class GoodName:
    """A well-documented class."""
    def __init__(self):
        pass

    def good_method(self):
        """A well-documented method."""
        return 42

def badName():
    pass
'''
        fpath = tmp_path / "sample.py"
        fpath.write_text(content)
        return str(fpath)

    def test_scan_file(self, intel, sample_python_file):
        issues = asyncio.get_event_loop().run_until_complete(
            intel.scan_file(sample_python_file)
        )
        assert isinstance(issues, list)
        assert len(issues) >= 1

    def test_scan_file_naming(self, intel, sample_python_file):
        issues = asyncio.get_event_loop().run_until_complete(
            intel.scan_file(sample_python_file)
        )
        naming = [i for i in issues if i.category == "naming"]
        assert len(naming) >= 1

    def test_scan_file_nonexistent(self, intel):
        issues = asyncio.get_event_loop().run_until_complete(
            intel.scan_file("/nonexistent/file.py")
        )
        assert issues == []

    def test_scan_jarvis_loop(self, intel):
        loop_path = os.path.join(
            os.path.dirname(__file__), "..", "jarvis", "brain", "loop.py"
        )
        issues = asyncio.get_event_loop().run_until_complete(
            intel.scan_file(loop_path)
        )
        assert isinstance(issues, list)

    def test_scan_project(self, intel):
        jarvis_path = os.path.join(os.path.dirname(__file__), "..")
        issues = asyncio.get_event_loop().run_until_complete(
            intel.scan_project(jarvis_path)
        )
        assert isinstance(issues, list)
        assert len(issues) >= 1

    def test_get_recommendations(self, intel):
        jarvis_path = os.path.join(os.path.dirname(__file__), "..")
        recs = asyncio.get_event_loop().run_until_complete(
            intel.get_recommendations(jarvis_path)
        )
        assert isinstance(recs, list)
        if recs:
            assert isinstance(recs[0], Recommendation)
            assert recs[0].priority_score >= 0

    def test_get_health(self, intel):
        jarvis_path = os.path.join(os.path.dirname(__file__), "..")
        health = asyncio.get_event_loop().run_until_complete(
            intel.get_health(jarvis_path)
        )
        assert isinstance(health, ProjectHealth)
        assert 0.0 <= health.overall_score <= 100.0

    def test_detect_drift(self, intel):
        jarvis_path = os.path.join(os.path.dirname(__file__), "..")
        drifts = asyncio.get_event_loop().run_until_complete(
            intel.detect_drift(jarvis_path)
        )
        assert isinstance(drifts, list)

    def test_watch_file(self, intel, sample_python_file):
        asyncio.get_event_loop().run_until_complete(intel.watch_file(sample_python_file))
        assert sample_python_file in intel._watched_files

    def test_check_watched_no_change(self, intel, sample_python_file):
        asyncio.get_event_loop().run_until_complete(intel.watch_file(sample_python_file))
        changed = asyncio.get_event_loop().run_until_complete(intel.check_watched())
        assert changed == []


# ---------------------------------------------------------------------------
# Individual Analyzers
# ---------------------------------------------------------------------------


class TestIndividualAnalyzers:
    def test_naming_checker_good(self):
        checker = NamingChecker()
        source = 'def snake_case():\n    pass\nclass GoodClass:\n    pass\n'
        issues = checker.analyze("test.py", source)
        assert len(issues) == 0

    def test_naming_checker_bad(self):
        checker = NamingChecker()
        source = 'def BadName():\n    pass\n'
        issues = checker.analyze("test.py", source)
        assert len(issues) == 1
        assert issues[0].category == "naming"

    def test_documentation_checker(self):
        checker = DocumentationChecker()
        source = 'def no_doc():\n    pass\n'
        issues = checker.analyze("test.py", source)
        assert len(issues) == 1
        assert issues[0].category == "documentation"

    def test_documentation_checker_with_docstring(self):
        checker = DocumentationChecker()
        source = 'def has_doc():\n    """Docstring."""\n    pass\n'
        issues = checker.analyze("test.py", source)
        assert len(issues) == 0

    def test_complexity_checker_simple(self):
        checker = ComplexityAnalyzer()
        source = 'def simple():\n    return 1\n'
        issues = checker.analyze("test.py", source)
        assert len(issues) == 0

    def test_duplication_detector(self):
        detector = DuplicationDetector()
        source = 'def foo():\n    return 1\n'
        detector.analyze("a.py", source)
        detector.analyze("b.py", source)
        dupes = detector.find_duplicates()
        assert len(dupes) >= 1

    def test_dead_code_detector_unused_import(self):
        detector = DeadCodeDetector()
        source = 'import os\nimport json\ndef main():\n    return os.path.exists(".")\n'
        issues = detector.analyze("test.py", source)
        unused = [i for i in issues if "unused" in i.description.lower()]
        assert len(unused) >= 1
        assert any("json" in i.description for i in unused)

    def test_dead_code_detector_all_used(self):
        detector = DeadCodeDetector()
        source = 'import os\ndef main():\n    return os.path.exists(".")\n'
        issues = detector.analyze("test.py", source)
        assert len(issues) == 0

    def test_architecture_drift_detector_bad_import(self):
        detector = ArchitectureDriftDetector()
        source = 'from jarvis.agents import AgentRegistry\n'
        issues = detector.analyze("/repo/jarvis/brain/loop.py", source)
        # brain importing from agents is a layer violation
        assert len(issues) >= 1

    def test_missing_test_detector(self, tmp_path):
        detector = MissingTestDetector()
        mod = tmp_path / "mymodule.py"
        mod.write_text('"""Module."""\n')
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        issues = detector.analyze_project(str(tmp_path), [str(mod)])
        assert len(issues) == 1
        assert "mymodule" in issues[0].description

    def test_stale_api_detector(self):
        detector = StaleAPIDetector()
        source = 'def public_func():\n    return 42\n'
        detector.record_file("mymod.py", source)
        stale = detector.find_stale()
        assert len(stale) >= 1

    def test_syntax_error_graceful(self):
        checker = NamingChecker()
        issues = checker.analyze("bad.py", "def (:\n")
        assert issues == []
