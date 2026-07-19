"""Memory privacy data models."""
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class PrivacyLevel(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    ENCRYPTED = "encrypted"
    FORGOTTEN = "forgotten"


class AuditAction(str, Enum):
    VIEW = "view"
    DELETE = "delete"
    FORGET = "forget"
    EXPORT = "export"
    IMPORT = "import"
    PAUSE = "pause"
    RESUME = "resume"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
    SEARCH = "search"


@dataclass
class MemoryPrivacySettings:
    paused: bool = False
    default_level: str = "private"
    encrypted_categories: List[str] = field(default_factory=list)
    forgotten_topics: List[str] = field(default_factory=list)
    private_projects: List[str] = field(default_factory=list)
    audit_enabled: bool = True
    auto_forget_days: int = 0  # 0 = never auto-forget

    def to_dict(self) -> dict:
        return {
            "paused": self.paused,
            "default_level": self.default_level,
            "encrypted_categories": self.encrypted_categories,
            "forgotten_topics": self.forgotten_topics,
            "private_projects": self.private_projects,
            "audit_enabled": self.audit_enabled,
            "auto_forget_days": self.auto_forget_days,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryPrivacySettings":
        return cls(
            paused=bool(data.get("paused", False)),
            default_level=str(data.get("default_level", "private")),
            encrypted_categories=data.get("encrypted_categories", []),
            forgotten_topics=data.get("forgotten_topics", []),
            private_projects=data.get("private_projects", []),
            audit_enabled=bool(data.get("audit_enabled", True)),
            auto_forget_days=int(data.get("auto_forget_days", 0)),
        )


@dataclass
class AuditEntry:
    id: str = ""
    action: str = "view"
    target: str = ""
    details: str = ""
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"audit_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "target": self.target,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        return cls(
            id=data.get("id", ""),
            action=data.get("action", "view"),
            target=data.get("target", ""),
            details=data.get("details", ""),
            timestamp=float(data.get("timestamp", 0.0)),
        )


@dataclass
class ExportData:
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    preferences: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    exported_at: float = 0.0

    def __post_init__(self):
        if not self.exported_at:
            self.exported_at = time.time()

    def to_dict(self) -> dict:
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "preferences": self.preferences,
            "decisions": self.decisions,
            "timeline": self.timeline,
            "exported_at": self.exported_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExportData":
        return cls(
            entities=data.get("entities", []),
            relationships=data.get("relationships", []),
            preferences=data.get("preferences", []),
            decisions=data.get("decisions", []),
            timeline=data.get("timeline", []),
            exported_at=float(data.get("exported_at", 0.0)),
        )
