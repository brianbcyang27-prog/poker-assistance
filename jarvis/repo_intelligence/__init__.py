"""Repository Intelligence engine for JARVIS v5.2.0.

Analyzes any Git repository and produces a comprehensive project profile.
"""

from .analyzer import RepoIntelligence
from .models import (
    ArchitectureReport,
    CodeStyleReport,
    DebtIssue,
    DebtReport,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    ImprovementItem,
    ImprovementReport,
    ProjectDNA,
)

__all__ = [
    "RepoIntelligence",
    "ProjectDNA",
    "DependencyGraph",
    "DependencyNode",
    "DependencyEdge",
    "ArchitectureReport",
    "CodeStyleReport",
    "DebtReport",
    "DebtIssue",
    "ImprovementReport",
    "ImprovementItem",
]
