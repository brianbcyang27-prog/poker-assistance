"""JARVIS v5.2.0 Autonomous Refactoring Engine.

Scans codebases for issues and generates refactoring proposals.
Never auto-applies changes - proposals require human review.
"""

from .engine import RefactoringEngine
from .models import IssueCategory, RefactorIssue, RefactorProposal, RiskLevel, Severity

__all__ = [
    "RefactoringEngine",
    "RefactorIssue",
    "RefactorProposal",
    "IssueCategory",
    "Severity",
    "RiskLevel",
]

__version__ = "5.2.0"
