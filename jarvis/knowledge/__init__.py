"""JARVIS Second Brain — Personal knowledge graph module.

⚠️  DEPRECATED: This package is being unified into ``jarvis.brain.memory.graph``.
    New code should import directly from ``jarvis.brain.memory.graph``.
    These re-exports exist for backward compatibility only.
"""

import warnings

from jarvis.brain.memory.graph import (
    Entity,
    EntityCluster,
    EntityType,
    GraphStats,
    ImportanceLevel,
    KnowledgeGraph,
    Relationship,
    RelationType,
)
from jarvis.knowledge.relationships import RelationshipEngine

__all__ = [
    "EntityType",
    "ImportanceLevel",
    "RelationType",
    "Entity",
    "Relationship",
    "EntityCluster",
    "GraphStats",
    "KnowledgeGraph",
    "RelationshipEngine",
]

warnings.warn(
    "jarvis.knowledge is deprecated. Import from jarvis.brain.memory.graph instead.",
    DeprecationWarning,
    stacklevel=2,
)
