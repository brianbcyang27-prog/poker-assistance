"""Mission data model — represents a single autonomous mission."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class MissionStatus(StrEnum):
    """Mission lifecycle status."""

    CREATED = "created"
    RESEARCHING = "researching"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class MissionStage(StrEnum):
    """Pipeline stages."""

    UNDERSTAND = "understand"
    RESEARCH = "research"
    DISCOVER = "discover"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    TEST = "test"
    REVIEW = "review"
    MEMORY = "memory"
    EVOLVE = "evolve"
    REPORT = "report"


@dataclass
class ResearchFinding:
    """A single research finding."""

    source: str  # github, pypi, docs, etc.
    title: str
    url: str = ""
    description: str = ""
    relevance: float = 0.0  # 0-1
    is_official: bool = False
    stars: int = 0
    language: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCandidate:
    """A discovered tool candidate."""

    name: str
    source: str  # pypi, npm, cargo, docker, etc.
    description: str = ""
    maturity: str = "unknown"  # mature, stable, beta, alpha, unknown
    install_command: str = ""
    language: str = ""
    stars: int = 0
    last_updated: str = ""
    score: float = 0.0  # 0-1 composite score
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchitecturePlan:
    """Engineering architecture plan."""

    objectives: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    modules: list[dict[str, str]] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    tradeoffs: list[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    files_to_modify: list[str] = field(default_factory=list)
    new_files: list[str] = field(default_factory=list)
    migration_plan: str = ""
    rollback_plan: str = ""
    testing_strategy: str = ""
    selected_tools: list[dict[str, str]] = field(default_factory=list)
    rejected_tools: list[dict[str, str]] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Result of a verification check."""

    check_type: str  # browser, vision, accessibility, api, file, build, test
    passed: bool
    evidence: str = ""
    screenshot_path: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReviewItem:
    """A self-review finding."""

    category: str  # success, failure, improvement, debt, refactor
    description: str
    severity: str = "info"  # info, warning, critical
    recommendation: str = ""


@dataclass
class MissionMemory:
    """Memory record from a completed mission."""

    mission_id: str
    problem: str
    solution: str
    libraries_used: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    architecture_decisions: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    benchmarks: dict[str, float] = field(default_factory=dict)
    successful_workflow: list[str] = field(default_factory=list)
    failure_workflow: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Mission:
    """A complete autonomous mission."""

    id: str = ""
    user_request: str = ""
    goal: str = ""
    owner: str = ""  # Card_id or user who owns this mission
    status: str = MissionStatus.CREATED
    current_stage: str = MissionStage.UNDERSTAND
    priority: str = "normal"

    # Pipeline outputs
    research_findings: list[ResearchFinding] = field(default_factory=list)
    tool_candidates: list[ToolCandidate] = field(default_factory=list)
    architecture_plan: ArchitecturePlan | None = None
    execution_results: list[dict[str, Any]] = field(default_factory=list)
    verification_results: list[VerificationResult] = field(default_factory=list)
    review_items: list[ReviewItem] = field(default_factory=list)
    memory_record: MissionMemory | None = None
    final_report: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    timeline_events: list[dict[str, Any]] = field(default_factory=list)
    stage_history: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"mission_{uuid.uuid4().hex[:12]}"

    def model_dump(self) -> dict[str, Any]:
        """Full serialization for database storage (matches Workspace.model_dump())."""

        def _serialize(val):
            if val is None:
                return None
            if hasattr(val, "__dict__"):
                return {k: _serialize(v) for k, v in val.__dict__.items() if not k.startswith("_")}
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, list):
                return [_serialize(v) for v in val]
            if isinstance(val, dict):
                return {k: _serialize(v) for k, v in val.items()}
            return val

        return {
            "id": self.id,
            "goal": self.goal,
            "owner": self.owner or "",
            "user_request": self.user_request,
            "status": self.status,
            "current_stage": self.current_stage,
            "progress": self._calculate_progress(),
            "priority": self.priority,
            "created_at": self.created_at.isoformat()
            if isinstance(self.created_at, datetime)
            else self.created_at,
            "started_at": self.started_at.isoformat()
            if isinstance(self.started_at, datetime)
            else self.started_at,
            "completed_at": self.completed_at.isoformat()
            if isinstance(self.completed_at, datetime)
            else self.completed_at,
            "duration_ms": self.duration_ms,
            "research_findings": _serialize(self.research_findings),
            "tool_candidates": _serialize(self.tool_candidates),
            "architecture_plan": _serialize(self.architecture_plan),
            "execution_results": _serialize(self.execution_results),
            "verification_results": _serialize(self.verification_results),
            "review_items": _serialize(self.review_items),
            "memory_record": _serialize(self.memory_record),
            "final_report": self.final_report,
            "timeline_events": _serialize(self.timeline_events),
            "stage_history": _serialize(self.stage_history),
            "errors": _serialize(self.errors),
        }

    def _calculate_progress(self) -> float:
        """Calculate progress based on pipeline completion."""
        if self.status in (MissionStatus.COMPLETED,):
            return 100.0
        stage_order = [
            MissionStage.UNDERSTAND,
            MissionStage.RESEARCH,
            MissionStage.DISCOVER,
            MissionStage.PLAN,
            MissionStage.EXECUTE,
            MissionStage.VERIFY,
            MissionStage.TEST,
            MissionStage.REVIEW,
            MissionStage.MEMORY,
            MissionStage.EVOLVE,
            MissionStage.REPORT,
        ]
        try:
            idx = stage_order.index(self.current_stage)
            return round((idx / len(stage_order)) * 100, 1)
        except ValueError:
            return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_request": self.user_request,
            "goal": self.goal,
            "status": self.status,
            "current_stage": self.current_stage,
            "priority": self.priority,
            "research_count": len(self.research_findings),
            "tools_discovered": len(self.tool_candidates),
            "has_plan": self.architecture_plan is not None,
            "execution_count": len(self.execution_results),
            "verification_count": len(self.verification_results),
            "verification_passed": sum(1 for v in self.verification_results if v.passed),
            "review_count": len(self.review_items),
            "has_memory": self.memory_record is not None,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
        }

    def stage_start(self, stage: str):
        """Record stage start."""
        self.current_stage = stage
        self.stage_history.append(
            {
                "stage": stage,
                "action": "start",
                "timestamp": datetime.now().isoformat(),
            }
        )

    def stage_complete(self, stage: str):
        """Record stage completion."""
        self.stage_history.append(
            {
                "stage": stage,
                "action": "complete",
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_error(self, error: str):
        """Add an error."""
        self.errors.append(f"[{self.current_stage}] {error}")
