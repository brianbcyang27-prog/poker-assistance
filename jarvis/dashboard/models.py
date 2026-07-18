"""Dashboard data models — metrics, health reports, and issues."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class HealthIssue:
    """A specific code quality issue found during analysis."""
    file: str
    line: int
    category: str
    severity: str  # critical, warning, info
    description: str
    suggestion: str
    auto_fixable: bool = False


@dataclass
class HealthReport:
    """Aggregated code health analysis result."""
    overall_score: float  # 0-100
    grades: Dict[str, str] = field(default_factory=dict)  # category -> A-F
    issues: List[HealthIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ProjectMetrics:
    """Complete project metrics snapshot."""
    health_score: float = 0.0
    architecture_score: float = 0.0
    debt_score: float = 0.0
    test_coverage: float = 0.0
    security_score: float = 0.0
    performance_score: float = 0.0
    complexity_score: float = 0.0
    duplication_score: float = 0.0
    dead_code_count: int = 0
    unused_files: int = 0
    unused_apis: int = 0
    dependency_issues: int = 0
    documentation_score: float = 0.0
    total_loc: int = 0
    total_files: int = 0
    total_classes: int = 0
    total_functions: int = 0
    total_tests: int = 0
    languages: Dict[str, int] = field(default_factory=dict)
    frameworks: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "health_score": self.health_score,
            "architecture_score": self.architecture_score,
            "debt_score": self.debt_score,
            "test_coverage": self.test_coverage,
            "security_score": self.security_score,
            "performance_score": self.performance_score,
            "complexity_score": self.complexity_score,
            "duplication_score": self.duplication_score,
            "dead_code_count": self.dead_code_count,
            "unused_files": self.unused_files,
            "unused_apis": self.unused_apis,
            "dependency_issues": self.dependency_issues,
            "documentation_score": self.documentation_score,
            "total_loc": self.total_loc,
            "total_files": self.total_files,
            "total_classes": self.total_classes,
            "total_functions": self.total_functions,
            "total_tests": self.total_tests,
            "languages": self.languages,
            "frameworks": self.frameworks,
            "generated_at": self.generated_at.isoformat(),
        }
