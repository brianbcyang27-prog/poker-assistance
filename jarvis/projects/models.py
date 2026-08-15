"""Project Intelligence — first-class Project models (v9.0.0 M2).

Projects are the living entities of JARVIS: a project owns its missions,
artifacts, decisions, and knowledge graph. Models here are the canonical
shapes returned by the `/api/projects` endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from ..domains.models import Domain


def _uuid8() -> str:
    return str(uuid.uuid4())[:8]


def _now() -> datetime:
    return datetime.now()


class Project(BaseModel):
    """A first-class JARVIS project."""

    id: str = Field(default_factory=_uuid8)
    name: str
    description: str = ""
    domain: str = Domain.ENGINEERING.value  # primary Domain.value
    status: str = "active"  # active | paused | archived | completed
    progress: float = 0.0
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
    last_worked_on: datetime | None = None
    workspace_ids: list[str] = Field(default_factory=list)
    mission_ids: list[str] = Field(default_factory=list)


class ProjectMission(BaseModel):
    """A mission scoped to a project."""

    id: str = Field(default_factory=_uuid8)
    project_id: str
    title: str
    goal: str
    complexity: str = "small"  # tiny | small | mission | project
    domain: str = Domain.ENGINEERING.value
    status: str = "planned"  # planned | active | completed | failed
    workspace_id: str | None = None
    created_at: datetime = Field(default_factory=_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Artifact(BaseModel):
    """A produced artifact (report, code, design, research...)."""

    id: str = Field(default_factory=_uuid8)
    project_id: str
    name: str
    artifact_type: str = "note"  # note | report | code | design | research | file
    content: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)


class ProjectDecision(BaseModel):
    """A recorded project decision with rationale."""

    id: str = Field(default_factory=_uuid8)
    project_id: str
    topic: str
    decision: str
    reason: str = ""
    context: str = ""
    created_at: datetime = Field(default_factory=_now)


class KnowledgeNode(BaseModel):
    """A node in the project knowledge graph."""

    id: str = Field(default_factory=_uuid8)
    project_id: str
    label: str
    node_type: str = "concept"  # concept | domain | artifact | decision | mission
    content: str = ""
    metadata: dict = Field(default_factory=dict)
    links: list[str] = Field(default_factory=list)  # linked node ids (edges)
    created_at: datetime = Field(default_factory=_now)
