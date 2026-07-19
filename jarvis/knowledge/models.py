"""Second Brain data models."""
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class EntityType(str, Enum):
    PERSON = "person"
    PROJECT = "project"
    ORGANIZATION = "organization"
    TECHNOLOGY = "technology"
    SKILL = "skill"
    CONCEPT = "concept"
    DECISION = "decision"
    GOAL = "goal"
    TASK = "task"
    DOCUMENT = "document"
    CODEBASE = "codebase"
    DEVICE = "device"
    LOCATION = "location"
    EVENT = "event"
    RESOURCE = "resource"


class ImportanceLevel(str, Enum):
    TEMPORARY = "temporary"
    USEFUL = "useful"
    IMPORTANT = "important"
    PERMANENT = "permanent"


class RelationType(str, Enum):
    CREATED = "created"
    USES = "uses"
    REQUIRES = "requires"
    INSPIRED_BY = "inspired_by"
    CAUSED = "caused"
    IMPROVED_BY = "improved_by"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    FOLLOWS = "follows"
    LEADS_TO = "leads_to"
    INFLUENCES = "influences"
    CONTAINS = "contains"
    MENTIONS = "mentions"
    WORKS_WITH = "works_with"


@dataclass
class Entity:
    id: str = ""
    name: str = ""
    entity_type: str = "concept"
    description: str = ""
    importance: str = "useful"
    confidence: float = 0.8
    source_memories: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    updated_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.entity_type}_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "description": self.description,
            "importance": self.importance,
            "confidence": self.confidence,
            "source_memories": self.source_memories,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Relationship:
    source_id: str = ""
    target_id: str = ""
    relation_type: str = "related_to"
    weight: float = 1.0
    description: str = ""
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "weight": self.weight,
            "description": self.description,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass
class EntityCluster:
    name: str = ""
    entities: List[Entity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    central_entity: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "central_entity": self.central_entity,
        }


@dataclass
class GraphStats:
    total_entities: int = 0
    total_relationships: int = 0
    entity_type_counts: Dict[str, int] = field(default_factory=dict)
    relationship_type_counts: Dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_importance: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships,
            "entity_type_counts": self.entity_type_counts,
            "relationship_type_counts": self.relationship_type_counts,
            "avg_confidence": self.avg_confidence,
            "avg_importance": self.avg_importance,
        }
