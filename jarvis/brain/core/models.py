"""Unified brain data models."""
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class BrainContext:
    """Complete context provided to every agent before execution."""
    current_goal: str = ""
    user_preferences: Dict[str, str] = field(default_factory=dict)
    relevant_memories: List[Dict[str, Any]] = field(default_factory=list)
    previous_attempts: List[Dict[str, Any]] = field(default_factory=list)
    project_context: Dict[str, Any] = field(default_factory=dict)
    available_tools: List[str] = field(default_factory=list)
    recent_decisions: List[Dict[str, Any]] = field(default_factory=list)
    timeline_events: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "current_goal": self.current_goal,
            "user_preferences": self.user_preferences,
            "relevant_memories": self.relevant_memories[:5],
            "previous_attempts": self.previous_attempts[:5],
            "project_context": self.project_context,
            "available_tools": self.available_tools,
            "recent_decisions": self.recent_decisions[:5],
            "timeline_events": self.timeline_events[:5],
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    def to_prompt_context(self) -> str:
        """Format context for LLM prompt injection."""
        lines = []
        if self.current_goal:
            lines.append(f"Goal: {self.current_goal}")
        if self.user_preferences:
            lines.append("Preferences:")
            for k, v in list(self.user_preferences.items())[:5]:
                lines.append(f"  - {k}: {v}")
        if self.relevant_memories:
            lines.append("Relevant memories:")
            for m in self.relevant_memories[:3]:
                lines.append(f"  - {m.get('content', m.get('name', 'unknown'))[:100]}")
        if self.recent_decisions:
            lines.append("Recent decisions:")
            for d in self.recent_decisions[:3]:
                lines.append(f"  - {d.get('title', 'unknown')}: {d.get('reason', '')[:80]}")
        if self.project_context:
            lines.append(f"Project: {self.project_context.get('name', 'unknown')}")
        lines.append(f"Confidence: {self.confidence:.0%}")
        return "\n".join(lines)


@dataclass
class MemoryEntry:
    """A single memory entry from any source."""
    id: str = ""
    content: str = ""
    source: str = ""  # conversation, extraction, consolidation, manual
    memory_type: str = ""  # fact, preference, decision, event, lesson
    importance: str = "useful"
    confidence: float = 0.8
    related_entities: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"mem_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "confidence": self.confidence,
            "related_entities": self.related_entities,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class ReasoningResult:
    """Result of a reasoning operation."""
    conclusion: str = ""
    confidence: float = 0.0
    reasoning_chain: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    supporting_memories: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "reasoning_chain": self.reasoning_chain,
            "alternatives": self.alternatives,
            "supporting_memories": self.supporting_memories,
            "warnings": self.warnings,
        }


@dataclass
class ActionDecision:
    """A decision about what action to take."""
    id: str = ""
    action: str = ""
    reason: str = ""
    confidence: float = 0.0
    alternatives_rejected: List[Dict[str, Any]] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    risk_level: str = "low"
    timestamp: float = 0.0

    def __post_init__(self):
        if not self.id:
            self.id = f"action_{uuid.uuid4().hex[:8]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "reason": self.reason,
            "confidence": self.confidence,
            "alternatives_rejected": self.alternatives_rejected,
            "supporting_evidence": self.supporting_evidence,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp,
        }
