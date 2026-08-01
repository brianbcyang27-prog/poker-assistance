"""
Base Architecture Interface - All AI agent architectures must implement this.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ArchitectureState(Enum):
    """States an architecture can be in."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    VERIFYING = "verifying"
    ERROR = "error"


@dataclass
class PlanStep:
    """A single step in a plan."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    tool: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    dependencies: list[str] = field(default_factory=list)  # step IDs
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tool": self.tool,
            "params": self.params,
            "expected_outcome": self.expected_outcome,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": str(self.result)[:500] if self.result else None,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Plan:
    """A complete plan for a mission."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ExecutionResult:
    """Result of executing a plan step."""

    step_id: str
    success: bool
    output: Any = None
    error: str | None = None
    verification: dict | None = None
    reflection: str | None = None
    duration_ms: float = 0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "verification": self.verification,
            "reflection": self.reflection,
            "duration_ms": self.duration_ms,
        }


@dataclass
class MissionContext:
    """Context for a mission execution."""

    mission_id: str
    user_request: str
    plan: Plan | None = None
    current_step: PlanStep | None = None
    executed_steps: list[ExecutionResult] = field(default_factory=list)
    working_memory: dict[str, Any] = field(default_factory=dict)
    long_term_memory: dict[str, Any] = field(default_factory=dict)
    tools_available: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class AgentArchitecture(ABC):
    """
    Base interface for all AI agent architectures.

    Every architecture must implement these core methods.
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.state = ArchitectureState.IDLE
        self.current_mission: MissionContext | None = None
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the architecture."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Version of the architecture."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this architecture does."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> list[str]:
        """List of capabilities this architecture supports."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the architecture. Returns True if successful."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean shutdown of the architecture."""
        pass

    @abstractmethod
    async def plan(self, mission: MissionContext) -> Plan:
        """
        Create a plan for the given mission.
        The architecture should decompose the goal into steps.
        """
        pass

    @abstractmethod
    async def execute(self, mission: MissionContext, plan: Plan) -> list[ExecutionResult]:
        """
        Execute the plan step by step.
        Returns list of execution results for each step.
        """
        pass

    @abstractmethod
    async def observe(
        self, mission: MissionContext, step_result: ExecutionResult
    ) -> dict[str, Any]:
        """
        Observe and analyze the result of a step execution.
        Returns observations that can inform next steps.
        """
        pass

    @abstractmethod
    async def reflect(self, mission: MissionContext) -> dict[str, Any]:
        """
        Reflect on the completed mission.
        Returns insights for learning/improvement.
        """
        pass

    @abstractmethod
    async def verify(self, step: PlanStep, result: ExecutionResult) -> dict[str, Any]:
        """
        Verify the result of a step execution.
        Returns verification result with confidence score.
        """
        pass

    @abstractmethod
    async def remember(
        self, mission: MissionContext, key: str, value: Any, memory_type: str = "working"
    ) -> None:
        """
        Store information in memory.
        memory_type: "working", "short_term", "long_term", "project"
        """
        pass

    @abstractmethod
    async def recall(self, mission: MissionContext, key: str, memory_type: str = "working") -> Any:
        """
        Retrieve information from memory.
        """
        pass

    @abstractmethod
    def get_status(self) -> dict[str, Any]:
        """Get current architecture status."""
        pass

    @abstractmethod
    def get_config_schema(self) -> dict[str, Any]:
        """Return JSON schema for configuration options."""
        pass


class ArchitectureRegistry:
    """Registry for managing available architectures."""

    def __init__(self):
        self._architectures: dict[str, AgentArchitecture] = {}
        self._default: str | None = None

    def register(self, architecture: AgentArchitecture) -> None:
        """Register an architecture instance."""
        arch_name = architecture.name.lower().replace(" ", "_")
        self._architectures[arch_name] = architecture
        if self._default is None:
            self._default = arch_name

    def get(self, name: str | None = None) -> AgentArchitecture | None:
        """Get an architecture by name, or the default."""
        if name is None:
            name = self._default
        if name:
            name = name.lower().replace(" ", "_")
        return self._architectures.get(name)

    def set_default(self, name: str) -> bool:
        """Set the default architecture."""
        name = name.lower().replace(" ", "_")
        if name in self._architectures:
            self._default = name
            return True
        return False

    def list(self) -> list[dict[str, Any]]:
        """List all registered architectures."""
        return [
            {
                "id": name,
                "name": arch.name,
                "version": arch.version,
                "description": arch.description,
                "capabilities": arch.capabilities,
                "is_default": name == self._default,
            }
            for name, arch in self._architectures.items()
        ]

    def unregister(self, name: str) -> bool:
        """Unregister an architecture."""
        name = name.lower().replace(" ", "_")
        if name in self._architectures:
            del self._architectures[name]
            if self._default == name:
                self._default = next(iter(self._architectures.keys()), None)
            return True
        return False
