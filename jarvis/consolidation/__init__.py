"""Memory Consolidation Engine module."""
from .models import (
    ConsolidationAction,
    ConsolidationResult,
    DuplicateGroup,
    MergeCandidate,
)
from .engine import ConsolidationEngine

__all__ = [
    "ConsolidationAction",
    "ConsolidationResult",
    "DuplicateGroup",
    "MergeCandidate",
    "ConsolidationEngine",
]
