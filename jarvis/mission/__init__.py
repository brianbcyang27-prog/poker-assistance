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
from .manager import MissionManager
from .loop import AutonomousLoop
from .replay import (
    MissionEvent, MissionReport, MissionReplayQuery, MissionEventType,
    MissionRecorder, MissionReplay,
)

__all__ = [
    "MissionPipeline",
    "MissionManager",
    "Mission",
    "MissionStage",
    "MissionStatus",
    "MissionMemory",
    "ResearchFinding",
    "ToolCandidate",
    "ArchitecturePlan",
    "VerificationResult",
    "ReviewItem",
    "AutonomousLoop",
    "MissionEvent",
    "MissionReport",
    "MissionReplayQuery",
    "MissionEventType",
    "MissionRecorder",
    "MissionReplay",
]
