"""Workspace router — unified mission tracking (v6.1.0)."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

import jarvis.web.main as web_main
from jarvis.core.database import get_db

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class CreateWorkspaceRequest(BaseModel):
    goal: str
    owner: str = "J"
    user_request: str = ""
    priority: str = "normal"


class TimelineEventRequest(BaseModel):
    event_type: str
    source: str
    description: str


class StageRequest(BaseModel):
    stage: str
    action: str = "start"


# === LIST ===

@router.get("")
async def list_workspaces(status: Optional[str] = None):
    """List active workspaces, optionally filtered by status."""
    if status:
        from jarvis.core.database import get_db
        db = await get_db()
        data = await db.get_all_workspaces(status=status)
        return data
    workspaces = await web_main.workspace_manager.get_active_workspaces()
    return [w.model_dump() for w in workspaces]


# === SEARCH ===

@router.get("/search")
async def search_workspaces(q: str = Query("", min_length=1), limit: int = 20):
    """Search workspaces by goal or user request."""
    return await web_main.workspace_manager.search_workspaces(q, limit)


# === HISTORY ===

@router.get("/history")
async def list_workspace_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List past completed workspaces from task history."""
    db = await get_db()
    history = await db.get_task_history(limit=limit, offset=offset)
    total = await db.get_task_history_count()
    return {"history": history, "total": total}


# === CREATE ===

@router.post("")
async def create_workspace(req: CreateWorkspaceRequest):
    """Create a new workspace."""
    workspace = await web_main.workspace_manager.create_workspace(
        goal=req.goal,
        owner=req.owner,
        user_request=req.user_request,
        priority=req.priority,
    )
    return workspace.model_dump()


# === GET ===

@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get full workspace details."""
    workspace = await web_main.workspace_manager.get_workspace(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}
    return workspace.model_dump()


@router.get("/{workspace_id}/status")
async def get_workspace_status(workspace_id: str):
    """Get lightweight workspace status for UI polling."""
    return await web_main.workspace_manager.get_workspace_status(workspace_id)


@router.get("/{workspace_id}/tasks")
async def get_workspace_tasks(workspace_id: str):
    """Get all tasks for a workspace."""
    db = await get_db()
    return await db.get_workspace_tasks(workspace_id)


@router.get("/{workspace_id}/timeline")
async def get_workspace_timeline(workspace_id: str):
    """Get the unified timeline for a workspace."""
    workspace = await web_main.workspace_manager.get_workspace(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}
    return {
        "events": workspace.timeline_events,
        "stages": workspace.stage_history,
        "total": len(workspace.timeline_events),
    }


@router.get("/{workspace_id}/replay")
async def replay_workspace(workspace_id: str):
    """Get recorded results for a workspace."""
    workspace = await web_main.workspace_manager.get_workspace(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}

    return {
        "workspace_id": workspace_id,
        "goal": workspace.goal,
        "owner": workspace.owner,
        "user_request": workspace.user_request,
        "status": workspace.status.value if hasattr(workspace.status, "value") else workspace.status,
        "final_report": workspace.final_report,
        "tasks": [
            {
                "id": t.id,
                "name": t.name,
                "assigned_to": t.assigned_to,
                "status": t.status.value if hasattr(t.status, "value") else t.status,
                "result": t.result,
                "confidence": t.confidence,
            }
            for t in workspace.tasks
        ],
        "timeline": workspace.timeline_events,
        "stages": workspace.stage_history,
        "research_count": len(workspace.research_findings),
        "verification_count": len(workspace.verification_results),
        "review_count": len(workspace.review_items),
        "errors": workspace.errors,
    }


# === MUTATIONS ===

@router.post("/{workspace_id}/timeline")
async def add_timeline_event(workspace_id: str, req: TimelineEventRequest):
    """Add a timeline event to a workspace."""
    ok = await web_main.workspace_manager.add_timeline_event(
        workspace_id, req.event_type, req.source, req.description,
    )
    if not ok:
        return {"error": "Workspace not found"}
    return {"ok": True}


@router.post("/{workspace_id}/stage")
async def record_stage(workspace_id: str, req: StageRequest):
    """Record a pipeline stage transition."""
    ok = await web_main.workspace_manager.record_stage(
        workspace_id, req.stage, req.action,
    )
    if not ok:
        return {"error": "Workspace not found"}
    return {"ok": True}


@router.post("/{workspace_id}/complete")
async def complete_workspace(workspace_id: str):
    """Mark a workspace as completed."""
    ok = await web_main.workspace_manager.complete_workspace(workspace_id)
    if not ok:
        return {"error": "Workspace not found"}
    return {"ok": True}
