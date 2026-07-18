"""JARVIS Mission Pipeline — Autonomous Research & Execution Engine.

Every non-trivial task follows this pipeline:
  1. Understand Goal
  2. Research
  3. Tool Discovery
  4. Architecture Planning
  5. Execution
  6. Verification
  7. Testing
  8. Self Review
  9. Memory Update
  10. Skill Evolution + Final Report
"""

from .pipeline import MissionPipeline
from .mission import (
    Mission, MissionStage, MissionStatus, MissionMemory,
    ResearchFinding, ToolCandidate, ArchitecturePlan,
    VerificationResult, ReviewItem,
)

__all__ = [
    "MissionPipeline",
    "Mission",
    "MissionStage",
    "MissionStatus",
    "MissionMemory",
    "ResearchFinding",
    "ToolCandidate",
    "ArchitecturePlan",
    "VerificationResult",
    "ReviewItem",
]
