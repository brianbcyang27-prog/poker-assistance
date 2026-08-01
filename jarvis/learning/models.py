"""Continuous Learning Engine data models."""

from dataclasses import dataclass


@dataclass
class LearningRecord:
    """Record of learnings from a completed mission."""

    mission_id: str
    libraries_discovered: list[str]
    patterns_learned: list[str]
    mistakes: list[str]
    speed_improvements: list[str]
    skill_suggestions: list[str]
    knowledge_updates: list[str]


@dataclass
class SkillUpdate:
    """Proposed update to an existing skill or new skill definition."""

    skill_name: str
    description: str
    before: str | None
    after: str
    reason: str
    confidence: float
