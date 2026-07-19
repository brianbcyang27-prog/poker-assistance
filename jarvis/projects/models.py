"""Data models for the JARVIS Project Awareness system."""

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


class BuildStatus(enum.Enum):
    """Build status of a project."""
    UNKNOWN = "unknown"
    PASSING = "passing"
    FAILING = "failing"
    BUILDING = "building"


@dataclass
class ProjectActivity:
    """Represents a single activity event in a project."""
    timestamp: datetime
    action: str
    detail: str
    files_affected: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action,
            "detail": self.detail,
            "files_affected": self.files_affected,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectActivity":
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action=data["action"],
            detail=data["detail"],
            files_affected=data.get("files_affected", []),
        )


@dataclass
class Project:
    """Represents a discovered or known project."""
    id: str
    name: str
    purpose: str
    path: str
    languages: List[str] = field(default_factory=list)
    frameworks: List[str] = field(default_factory=list)
    git_remote: Optional[str] = None
    git_branch: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    architecture: Optional[str] = None
    known_issues: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)
    open_prs: List[str] = field(default_factory=list)
    build_status: BuildStatus = BuildStatus.UNKNOWN
    recent_commits: List[str] = field(default_factory=list)
    documentation_score: float = 0.0
    last_accessed: Optional[datetime] = None
    context_snapshot: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "purpose": self.purpose,
            "path": self.path,
            "languages": self.languages,
            "frameworks": self.frameworks,
            "git_remote": self.git_remote,
            "git_branch": self.git_branch,
            "dependencies": self.dependencies,
            "architecture": self.architecture,
            "known_issues": self.known_issues,
            "todos": self.todos,
            "open_prs": self.open_prs,
            "build_status": self.build_status.value,
            "recent_commits": self.recent_commits,
            "documentation_score": self.documentation_score,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "context_snapshot": self.context_snapshot,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Create from dictionary."""
        last_accessed = None
        if data.get("last_accessed"):
            last_accessed = datetime.fromisoformat(data["last_accessed"])

        return cls(
            id=data["id"],
            name=data["name"],
            purpose=data["purpose"],
            path=data["path"],
            languages=data.get("languages", []),
            frameworks=data.get("frameworks", []),
            git_remote=data.get("git_remote"),
            git_branch=data.get("git_branch"),
            dependencies=data.get("dependencies", []),
            architecture=data.get("architecture"),
            known_issues=data.get("known_issues", []),
            todos=data.get("todos", []),
            open_prs=data.get("open_prs", []),
            build_status=BuildStatus(data.get("build_status", "unknown")),
            recent_commits=data.get("recent_commits", []),
            documentation_score=data.get("documentation_score", 0.0),
            last_accessed=last_accessed,
            context_snapshot=data.get("context_snapshot", {}),
            metadata=data.get("metadata", {}),
        )
