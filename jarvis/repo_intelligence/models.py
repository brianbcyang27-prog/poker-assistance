"""Data models for Repository Intelligence engine."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class DependencyNode:
    name: str
    version: str
    type: str  # direct, dev, optional
    ecosystem: str  # pypi, npm, cargo, etc.


@dataclass
class DependencyEdge:
    source: str
    target: str
    type: str  # requires, peer, dev


@dataclass
class DependencyGraph:
    nodes: List[DependencyNode] = field(default_factory=list)
    edges: List[DependencyEdge] = field(default_factory=list)


@dataclass
class ArchitectureReport:
    style: str  # monolith, microservices, layered, etc.
    modules: List[str] = field(default_factory=list)
    layers: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    api_routes: List[str] = field(default_factory=list)
    database_tables: List[str] = field(default_factory=list)
    config_files: List[str] = field(default_factory=list)


@dataclass
class CodeStyleReport:
    avg_line_length: float = 0.0
    max_function_length: int = 0
    avg_function_length: float = 0.0
    naming_convention: str = "unknown"
    docstring_coverage: float = 0.0
    type_hint_coverage: float = 0.0


@dataclass
class DebtIssue:
    file: str
    line: int
    category: str  # duplication, complexity, unused, import, dead_code, naming
    description: str
    severity: str  # low, medium, high, critical
    suggestion: str


@dataclass
class DebtReport:
    score: float  # 0-100, lower is better
    issues: List[DebtIssue] = field(default_factory=list)
    summary: str = ""


@dataclass
class ImprovementItem:
    category: str
    description: str
    impact: str  # low, medium, high
    effort: str  # low, medium, high
    files_affected: List[str] = field(default_factory=list)


@dataclass
class ImprovementReport:
    items: List[ImprovementItem] = field(default_factory=list)
    priority_score: float = 0.0


@dataclass
class ProjectDNA:
    name: str = ""
    purpose: str = ""
    languages: Dict[str, float] = field(default_factory=dict)
    frameworks: List[str] = field(default_factory=list)
    build_system: Dict[str, str] = field(default_factory=dict)
    package_managers: List[str] = field(default_factory=list)
    architecture_style: str = "unknown"
    folder_structure: Dict[str, int] = field(default_factory=dict)
    coding_style: Optional[CodeStyleReport] = None
    patterns: List[str] = field(default_factory=list)
    testing_framework: str = "unknown"
    deployment_method: str = "unknown"
    ci_cd: List[str] = field(default_factory=list)
    documentation_quality: float = 0.0
    debt_score: float = 0.0
    health_score: float = 0.0
    risk_score: float = 0.0
