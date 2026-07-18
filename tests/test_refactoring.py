"""Tests for JARVIS Refactoring Engine (v5.2.0)."""

import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jarvis.refactoring import (
    RefactoringEngine,
    RefactorIssue,
    RefactorProposal,
    IssueCategory,
    Severity,
    RiskLevel,
)

REPO_PATH = os.path.join(os.path.dirname(__file__), "..")


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ════════════════════════════════════════════════════════════
# Data Model Tests
# ════════════════════════════════════════════════════════════

class TestRefactorModels:
    def test_refactor_issue(self):
        issue = RefactorIssue(
            file="main.py", line=10, category=IssueCategory.NAMING,
            description="Bad name", severity=Severity.LOW,
            code_snippet="def badName():", suggestion="Rename to snake_case",
        )
        assert issue.file == "main.py"
        assert issue.category == IssueCategory.NAMING
        d = issue.to_dict()
        assert d["category"] == "naming"

    def test_refactor_proposal(self):
        proposal = RefactorProposal(
            title="Fix naming", description="Fix all naming issues",
            issues=[], before_code="old", after_code="new",
            benefits=["Better readability"], risk=RiskLevel.LOW,
            estimated_impact="Low", files_affected=["a.py"],
            auto_applicable=True,
        )
        assert proposal.risk == RiskLevel.LOW
        d = proposal.to_dict()
        assert d["risk"] == "low"
        assert d["auto_applicable"] is True

    def test_issue_categories(self):
        assert IssueCategory.DUPLICATION.value == "duplication"
        assert IssueCategory.COMPLEXITY.value == "complexity"
        assert IssueCategory.HIGH_COMPLEXITY.value == "high_complexity"

    def test_severity_levels(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"

    def test_risk_levels(self):
        assert RiskLevel.MEDIUM.value == "medium"


# ════════════════════════════════════════════════════════════
# Engine Tests (against jarvis repo)
# ════════════════════════════════════════════════════════════

class TestRefactoringEngine:
    def setup_method(self):
        self.engine = RefactoringEngine()

    def test_scan_duplicates(self):
        issues = _run(self.engine.scan_duplicates(REPO_PATH))
        assert isinstance(issues, list)

    def test_scan_large_functions(self):
        issues = _run(self.engine.scan_large_functions(REPO_PATH))
        assert isinstance(issues, list)
        for issue in issues:
            assert issue.category == IssueCategory.CODE_SMELL

    def test_scan_naming(self):
        issues = _run(self.engine.scan_naming(REPO_PATH))
        assert isinstance(issues, list)

    def test_scan_unused(self):
        issues = _run(self.engine.scan_unused(REPO_PATH))
        assert isinstance(issues, list)

    def test_scan_circular_imports(self):
        issues = _run(self.engine.scan_circular_imports(REPO_PATH))
        assert isinstance(issues, list)

    def test_scan_code_smells(self):
        issues = _run(self.engine.scan_code_smells(REPO_PATH))
        assert isinstance(issues, list)

    def test_scan_long_files(self):
        issues = _run(self.engine.scan_long_files(REPO_PATH))
        assert isinstance(issues, list)
        for issue in issues:
            assert issue.category == IssueCategory.LONG_FILE

    def test_scan_missing_docs(self):
        issues = _run(self.engine.scan_missing_docs(REPO_PATH))
        assert isinstance(issues, list)
        for issue in issues:
            assert issue.category == IssueCategory.MISSING_DOC

    def test_scan_high_complexity(self):
        issues = _run(self.engine.scan_high_complexity(REPO_PATH))
        assert isinstance(issues, list)

    def test_full_scan(self):
        issues = _run(self.engine.scan(REPO_PATH))
        assert isinstance(issues, list)
        assert len(issues) > 0
        categories = set(i.category for i in issues)
        assert len(categories) > 0

    def test_generate_proposals(self):
        issues = _run(self.engine.scan(REPO_PATH))
        proposals = _run(self.engine.generate_proposals(issues))
        assert isinstance(proposals, list)
        assert len(proposals) > 0
        for p in proposals:
            assert isinstance(p, RefactorProposal)
            assert p.title != ""
            assert p.description != ""
            assert isinstance(p.benefits, list)
            assert isinstance(p.files_affected, list)
