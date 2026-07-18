"""Mission data model — represents a single autonomous mission."""

import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


class MissionStatus(str, Enum):
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


class MissionStage(str, Enum):
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
    source: str           # github, pypi, docs, etc.
    title: str
    url: str = ""
    description: str = ""
    relevance: float = 0.0  # 0-1
    is_official: bool = False
    stars: int = 0
    language: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCandidate:
    """A discovered tool candidate."""
    name: str
    source: str           # pypi, npm, cargo, docker, etc.
    description: str = ""
    maturity: str = "unknown"  # mature, stable, beta, alpha, unknown
    install_command: str = ""
    language: str = ""
    stars: int = 0
    last_updated: str = ""
    score: float = 0.0    # 0-1 composite score
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArchitecturePlan:
    """Engineering architecture plan."""
    objectives: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    modules: List[Dict[str, str]] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    tradeoffs: List[str] = field(default_factory=list)
    estimated_hours: float = 0.0
    files_to_modify: List[str] = field(default_factory=list)
    new_files: List[str] = field(default_factory=list)
    migration_plan: str = ""
    rollback_plan: str = ""
    testing_strategy: str = ""
    selected_tools: List[Dict[str, str]] = field(default_factory=list)
    rejected_tools: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Result of a verification check."""
    check_type: str       # browser, vision, accessibility, api, file, build, test
    passed: bool
    evidence: str = ""
    screenshot_path: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReviewItem:
    """A self-review finding."""
    category: str         # success, failure, improvement, debt, refactor
    description: str
    severity: str = "info"  # info, warning, critical
    recommendation: str = ""


@dataclass
class MissionMemory:
    """Memory record from a completed mission."""
    mission_id: str
    problem: str
    solution: str
    libraries_used: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    architecture_decisions: List[str] = field(default_factory=list)
    mistakes: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    benchmarks: Dict[str, float] = field(default_factory=dict)
    successful_workflow: List[str] = field(default_factory=list)
    failure_workflow: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Mission:
    """A complete autonomous mission."""
    id: str = ""
    user_request: str = ""
    goal: str = ""
    status: str = MissionStatus.CREATED
    current_stage: str = MissionStage.UNDERSTAND
    priority: str = "normal"

    # Pipeline outputs
    research_findings: List[ResearchFinding] = field(default_factory=list)
    tool_candidates: List[ToolCandidate] = field(default_factory=list)
    architecture_plan: Optional[ArchitecturePlan] = None
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    verification_results: List[VerificationResult] = field(default_factory=list)
    review_items: List[ReviewItem] = field(default_factory=list)
    memory_record: Optional[MissionMemory] = None
    final_report: str = ""

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"mission_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> Dict[str, Any]:
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
        self.stage_history.append({
            "stage": stage,
            "action": "start",
            "timestamp": datetime.now().isoformat(),
        })

    def stage_complete(self, stage: str):
        """Record stage completion."""
        self.stage_history.append({
            "stage": stage,
            "action": "complete",
            "timestamp": datetime.now().isoformat(),
        })

    def add_error(self, error: str):
        """Add an error."""
        self.errors.append(f"[{self.current_stage}] {error}")
