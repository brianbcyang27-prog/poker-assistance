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

from .loop import AutonomousLoop
from .manager import MissionManager
from .mission import (
    ArchitecturePlan,
    Mission,
    MissionMemory,
    MissionStage,
    MissionStatus,
    ResearchFinding,
    ReviewItem,
    ToolCandidate,
    VerificationResult,
)
from .pipeline import MissionPipeline
from .replay import (
    MissionEvent,
    MissionEventType,
    MissionRecorder,
    MissionReplay,
    MissionReplayQuery,
    MissionReport,
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
