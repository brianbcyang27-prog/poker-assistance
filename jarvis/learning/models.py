"""Continuous Learning Engine data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LearningRecord:
    """Record of learnings from a completed mission."""

    mission_id: str
    libraries_discovered: List[str]
    patterns_learned: List[str]
    mistakes: List[str]
    speed_improvements: List[str]
    skill_suggestions: List[str]
    knowledge_updates: List[str]


@dataclass
class SkillUpdate:
    """Proposed update to an existing skill or new skill definition."""

    skill_name: str
    description: str
    before: Optional[str]
    after: str
    reason: str
    confidence: float
