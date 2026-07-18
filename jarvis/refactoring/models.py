"""Data models for the JARVIS Refactoring Engine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class IssueCategory(Enum):
    """Categories of refactoring issues."""
    DUPLICATION = "duplication"
    COMPLEXITY = "complexity"
    NAMING = "naming"
    UNUSED = "unused"
    CIRCULAR_IMPORT = "circular_import"
    CODE_SMELL = "code_smell"
    LONG_FILE = "long_file"
    MISSING_DOC = "missing_doc"
    HIGH_COMPLEXITY = "high_complexity"


class Severity(Enum):
    """Severity levels for issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """Risk levels for refactoring proposals."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RefactorIssue:
    """Represents a code issue found during scanning."""
    file: str
    line: int
    category: IssueCategory
    description: str
    severity: Severity
    code_snippet: str
    suggestion: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "category": self.category.value,
            "description": self.description,
            "severity": self.severity.value,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
        }


@dataclass
class RefactorProposal:
    """Represents a refactoring proposal (PR-style)."""
    title: str
    description: str
    issues: List[RefactorIssue]
    before_code: str
    after_code: str
    benefits: List[str]
    risk: RiskLevel
    estimated_impact: str
    files_affected: List[str]
    auto_applicable: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "description": self.description,
            "issues": [i.to_dict() for i in self.issues],
            "before_code": self.before_code,
            "after_code": self.after_code,
            "benefits": self.benefits,
            "risk": self.risk.value,
            "estimated_impact": self.estimated_impact,
            "files_affected": self.files_affected,
            "auto_applicable": self.auto_applicable,
        }
