"""Memory extraction data models."""
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ExtractedType(str, Enum):
    FACT = "fact"
    DECISION = "decision"
    PREFERENCE = "preference"
    PROJECT = "project"
    TECHNOLOGY = "technology"
    PERSON = "person"
    LESSON = "lesson"
    GOAL = "goal"
    TASK = "task"
    EVENT = "event"


class ImportanceLevel(str, Enum):
    TEMPORARY = "temporary"
    USEFUL = "useful"
    IMPORTANT = "important"
    PERMANENT = "permanent"


@dataclass
class ExtractionResult:
    source_text: str = ""
    extracted_items: List[Dict[str, Any]] = field(default_factory=list)
    entities_created: List[str] = field(default_factory=list)
    relationships_created: List[str] = field(default_factory=list)
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "source_text": self.source_text[:200],
            "extracted_count": len(self.extracted_items),
            "entities_created": self.entities_created,
            "relationships_created": self.relationships_created,
            "timestamp": self.timestamp,
        }


@dataclass
class ExtractedMemory:
    content: str = ""
    extracted_type: str = "fact"
    importance: str = "useful"
    confidence: float = 0.7
    source: str = ""
    related_entities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "extracted_type": self.extracted_type,
            "importance": self.importance,
            "confidence": self.confidence,
            "source": self.source,
            "related_entities": self.related_entities,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }
