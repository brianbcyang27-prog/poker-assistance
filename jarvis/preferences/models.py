"""Preference learning data models."""
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class PreferenceCategory(str, Enum):
    CODING = "coding"
    HARDWARE = "hardware"
    COMMUNICATION = "communication"
    TOOLS = "tools"
    WORKFLOW = "workflow"
    DESIGN = "design"
    DEPLOYMENT = "deployment"
    LEARNING = "learning"
    GENERAL = "general"


@dataclass
class Preference:
    id: str = ""
    category: str = "general"
    key: str = ""
    value: str = ""
    confidence: float = 0.8
    source: str = ""
    evidence: List[str] = field(default_factory=list)
    first_seen: float = 0.0
    last_seen: float = 0.0
    times_reinforced: int = 1

    def __post_init__(self):
        if not self.id:
            self.id = f"pref_{uuid.uuid4().hex[:8]}"
        now = time.time()
        if not self.first_seen:
            self.first_seen = now
        if not self.last_seen:
            self.last_seen = now

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "evidence": self.evidence,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "times_reinforced": self.times_reinforced,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Preference":
        return cls(
            id=data.get("id", ""),
            category=data.get("category", "general"),
            key=data.get("key", ""),
            value=data.get("value", ""),
            confidence=float(data.get("confidence", 0.8)),
            source=data.get("source", ""),
            evidence=data.get("evidence", []),
            first_seen=float(data.get("first_seen", 0.0)),
            last_seen=float(data.get("last_seen", 0.0)),
            times_reinforced=int(data.get("times_reinforced", 1)),
        )


@dataclass
class PreferenceProfile:
    category: str = ""
    preferences: List[Preference] = field(default_factory=list)
    dominant_values: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "preferences": [p.to_dict() for p in self.preferences],
            "dominant_values": self.dominant_values,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreferenceProfile":
        return cls(
            category=data.get("category", ""),
            preferences=[Preference.from_dict(p) for p in data.get("preferences", [])],
            dominant_values=data.get("dominant_values", {}),
        )
