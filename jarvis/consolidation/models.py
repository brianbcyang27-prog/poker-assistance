"""Memory consolidation data models."""
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ConsolidationAction(str, Enum):
    DEDUPLICATE = "deduplicate"
    MERGE = "merge"
    STRENGTHEN = "strengthen"
    SUMMARIZE = "summarize"
    FORGET = "forget"


@dataclass
class ConsolidationResult:
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    duplicates_removed: int = 0
    memories_merged: int = 0
    memories_strengthened: int = 0
    memories_summarized: int = 0
    memories_forgotten: int = 0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "actions_taken": len(self.actions_taken),
            "duplicates_removed": self.duplicates_removed,
            "memories_merged": self.memories_merged,
            "memories_strengthened": self.memories_strengthened,
            "memories_summarized": self.memories_summarized,
            "memories_forgotten": self.memories_forgotten,
            "timestamp": self.timestamp,
        }


@dataclass
class DuplicateGroup:
    entity_ids: List[str] = field(default_factory=list)
    reason: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "entity_ids": self.entity_ids,
            "reason": self.reason,
            "confidence": self.confidence,
        }


@dataclass
class MergeCandidate:
    primary_id: str = ""
    secondary_id: str = ""
    reason: str = ""
    combined_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "primary_id": self.primary_id,
            "secondary_id": self.secondary_id,
            "reason": self.reason,
            "combined_data": self.combined_data,
        }
