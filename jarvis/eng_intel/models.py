"""Engineering Intelligence data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class IssueCategory(Enum):
    DUPLICATION = "duplication"
    NAMING = "naming"
    DOCUMENTATION = "documentation"
    COMPLEXITY = "complexity"
    DEAD_CODE = "dead_code"
    CIRCULAR_IMPORT = "circular_import"
    STALE_API = "stale_api"
    MISSING_TEST = "missing_test"


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Impact(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Effort(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class EngineeringIssue:
    """A code quality or architecture issue found during analysis."""
    id: str
    timestamp: str
    file_path: str
    line: int
    category: str
    severity: str
    description: str
    suggestion: str
    auto_fixable: bool = False
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "file_path": self.file_path,
            "line": self.line,
            "category": self.category,
            "severity": self.severity,
            "description": self.description,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
            "confidence": self.confidence,
        }


@dataclass
class Recommendation:
    """An improvement recommendation for a project."""
    id: str
    category: str
    title: str
    description: str
    impact: str
    effort: str
    files_affected: List[str] = field(default_factory=list)
    priority_score: float = 0.0

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "effort": self.effort,
            "files_affected": self.files_affected,
            "priority_score": self.priority_score,
        }


@dataclass
class ProjectHealth:
    """Aggregated project health summary."""
    overall_score: float
    grades: Dict[str, str] = field(default_factory=dict)
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    trends: Dict[str, str] = field(default_factory=dict)
    last_scan: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            "overall_score": self.overall_score,
            "grades": self.grades,
            "issues_by_category": self.issues_by_category,
            "trends": self.trends,
            "last_scan": self.last_scan,
        }


@dataclass
class DriftIssue:
    """An architectural drift detected in the project."""
    module: str
    expected_pattern: str
    actual_pattern: str
    description: str
    severity: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "module": self.module,
            "expected_pattern": self.expected_pattern,
            "actual_pattern": self.actual_pattern,
            "description": self.description,
            "severity": self.severity,
        }
