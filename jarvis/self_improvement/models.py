"""Self-improvement data models."""
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(str, Enum):
    RETRY = "retry"
    FIX_DEPENDENCY = "fix_dependency"
    ALTERNATIVE_APPROACH = "alternative_approach"
    SKIP = "skip"
    ESCALATE = "escalate"
    ASK_USER = "ask_user"


@dataclass
class ErrorRecord:
    id: str = ""
    error_type: str = ""
    message: str = ""
    module: str = ""
    function: str = ""
    severity: str = "medium"
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    solution: str = ""
    prevention: str = ""
    occurred_at: float = 0.0
    resolved: bool = False
    resolution: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"err_{uuid.uuid4().hex[:8]}"
        if not self.occurred_at:
            self.occurred_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "error_type": self.error_type,
            "message": self.message,
            "module": self.module,
            "function": self.function,
            "severity": self.severity,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "solution": self.solution,
            "prevention": self.prevention,
            "occurred_at": self.occurred_at,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorRecord":
        return cls(
            id=data.get("id", ""),
            error_type=data.get("error_type", ""),
            message=data.get("message", ""),
            module=data.get("module", ""),
            function=data.get("function", ""),
            severity=data.get("severity", "medium"),
            stack_trace=data.get("stack_trace", ""),
            context=data.get("context", {}),
            solution=data.get("solution", ""),
            prevention=data.get("prevention", ""),
            occurred_at=float(data.get("occurred_at", 0.0)),
            resolved=bool(data.get("resolved", False)),
            resolution=data.get("resolution", ""),
        )


@dataclass
class RecoveryPlan:
    error_id: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    requires_permission: bool = True
    estimated_time: str = ""
    fallback: str = ""

    def to_dict(self) -> dict:
        return {
            "error_id": self.error_id,
            "actions": self.actions,
            "confidence": self.confidence,
            "requires_permission": self.requires_permission,
            "estimated_time": self.estimated_time,
            "fallback": self.fallback,
        }


@dataclass
class Lesson:
    id: str = ""
    category: str = ""
    description: str = ""
    trigger: str = ""  # what caused this lesson
    action: str = ""  # what to do instead
    confidence: float = 0.8
    times_applied: int = 0
    created_at: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"lesson_{uuid.uuid4().hex[:8]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "description": self.description,
            "trigger": self.trigger,
            "action": self.action,
            "confidence": self.confidence,
            "times_applied": self.times_applied,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lesson":
        return cls(
            id=data.get("id", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            trigger=data.get("trigger", ""),
            action=data.get("action", ""),
            confidence=float(data.get("confidence", 0.8)),
            times_applied=int(data.get("times_applied", 0)),
            created_at=float(data.get("created_at", 0.0)),
        )
