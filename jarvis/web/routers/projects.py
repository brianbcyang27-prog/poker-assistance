"""Projects router — /api/projects (v9.0.0 M2 Project Intelligence)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import jarvis.web.main as web_main
from jarvis.projects.complexity import estimate_complexity
from jarvis.projects.manager import project_manager

router = APIRouter(prefix="/api/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    domain: str = "engineering"


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    domain: str | None = None
    status: str | None = None


class CreateMissionRequest(BaseModel):
    title: str
    goal: str = ""
    complexity: str = "small"
    domain: str = "engineering"


class AddArtifactRequest(BaseModel):
    name: str
    artifact_type: str = "note"
    content: str = ""


class AddDecisionRequest(BaseModel):
    topic: str
    decision: str
    reason: str = ""
    context: str = ""


class AddKnowledgeRequest(BaseModel):
    label: str
    node_type: str = "concept"
    content: str = ""
    links: list[str] = []


class LinkWorkspaceRequest(BaseModel):
    workspace_id: str


def _manager():
    if web_main.project_manager is None:
        raise HTTPException(status_code=503, detail="Project manager not initialized")
    return web_main.project_manager


@router.get("")
async def list_projects(status: str | None = None, limit: int = 100):
    """List projects (optionally filtered by status)."""
    projects = await project_manager.list_projects(status=status, limit=limit)
    return {"projects": [p.model_dump(mode="json") for p in projects], "total": len(projects)}


@router.post("")
async def create_project(req: CreateProjectRequest):
    """Create a project (or return the existing one with the same name)."""
    project = await project_manager.create_project(
        name=req.name, description=req.description, domain=req.domain
    )
    return project.model_dump(mode="json")


@router.get("/{project_id}")
async def get_project(project_id: str):
    """Get a single project."""
    project = await project_manager.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project.model_dump(mode="json")


@router.patch("/{project_id}")
async def update_project(project_id: str, req: UpdateProjectRequest):
    """Update project fields."""
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    project = await project_manager.update_project(project_id, **fields)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return project.model_dump(mode="json")


@router.get("/{project_id}/dashboard")
async def project_dashboard(project_id: str):
    """Aggregated dashboard data for a project."""
    data = await project_manager.dashboard(project_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return data


@router.get("/{project_id}/timeline")
async def project_timeline(project_id: str):
    """Mission timeline as {nodes, edges} for the DAG view."""
    timeline = await project_manager.timeline(project_id)
    if not timeline["nodes"] and not await project_manager.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
    return timeline


@router.get("/{project_id}/missions")
async def list_missions(project_id: str, status: str | None = None):
    """List missions for a project."""
    missions = await project_manager.list_missions(project_id=project_id, status=status)
    return {"missions": [m.model_dump(mode="json") for m in missions], "total": len(missions)}


@router.post("/{project_id}/missions")
async def create_mission(project_id: str, req: CreateMissionRequest):
    """Create a mission under a project."""
    mission = await project_manager.add_mission(
        project_id=project_id,
        title=req.title,
        goal=req.goal or req.title,
        complexity=req.complexity,
        domain=req.domain,
    )
    return mission.model_dump(mode="json")


@router.post("/{project_id}/artifacts")
async def add_artifact(project_id: str, req: AddArtifactRequest):
    """Add an artifact to a project."""
    artifact = await project_manager.add_artifact(
        project_id=project_id,
        name=req.name,
        artifact_type=req.artifact_type,
        content=req.content,
    )
    return artifact.model_dump(mode="json")


@router.get("/{project_id}/artifacts")
async def list_artifacts(project_id: str, limit: int = 100):
    """List artifacts for a project."""
    artifacts = await project_manager.list_artifacts(project_id=project_id, limit=limit)
    return {"artifacts": [a.model_dump(mode="json") for a in artifacts], "total": len(artifacts)}


@router.post("/{project_id}/decisions")
async def add_decision(project_id: str, req: AddDecisionRequest):
    """Record a decision for a project."""
    decision = await project_manager.add_decision(
        project_id=project_id,
        topic=req.topic,
        decision=req.decision,
        reason=req.reason,
        context=req.context,
    )
    return decision.model_dump(mode="json")


@router.get("/{project_id}/decisions")
async def list_decisions(project_id: str, limit: int = 100):
    """List decisions for a project."""
    decisions = await project_manager.list_decisions(project_id=project_id, limit=limit)
    return {"decisions": [d.model_dump(mode="json") for d in decisions], "total": len(decisions)}


@router.post("/{project_id}/knowledge")
async def add_knowledge(project_id: str, req: AddKnowledgeRequest):
    """Add a node to the project knowledge graph."""
    node = await project_manager.add_knowledge(
        project_id=project_id,
        label=req.label,
        node_type=req.node_type,
        content=req.content,
        links=req.links,
    )
    return node.model_dump(mode="json")


@router.get("/{project_id}/knowledge")
async def list_knowledge(project_id: str):
    """List knowledge graph nodes (each carries its links for edges)."""
    nodes = await project_manager.list_knowledge(project_id=project_id)
    return {"nodes": [n.model_dump(mode="json") for n in nodes], "total": len(nodes)}


@router.post("/{project_id}/link-workspace")
async def link_workspace(project_id: str, req: LinkWorkspaceRequest):
    """Link an execution workspace to the project."""
    await project_manager.link_workspace(project_id, req.workspace_id)
    return {"ok": True, "project_id": project_id, "workspace_id": req.workspace_id}


@router.post("/estimate")
async def estimate(req: dict):
    """Estimate the complexity of a free-form request (used by the task flow)."""
    request = req.get("message", "")
    return estimate_complexity(request)
