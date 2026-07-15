"""Workspace router - Mission tracking."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from jarvis.web.main import workspace_manager, jarvis
from jarvis.core.models import Task
from jarvis.core.database import get_db

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class CreateWorkspaceRequest(BaseModel):
    goal: str
    owner: str = "♠K"


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


@router.post("")
async def create_workspace(req: CreateWorkspaceRequest):
    """Create a new workspace."""
    workspace = await workspace_manager.create_workspace(
        goal=req.goal,
        owner=req.owner,
    )
    return workspace.model_dump()


@router.get("")
async def list_workspaces():
    """List all active workspaces."""
    workspaces = await workspace_manager.get_active_workspaces()
    return [w.model_dump() for w in workspaces]


@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str):
    """Get workspace details."""
    workspace = await workspace_manager.get_workspace(workspace_id)
    if not workspace:
        return {"error": "Workspace not found"}
    return workspace.model_dump()


@router.get("/{workspace_id}/status")
async def get_workspace_status(workspace_id: str):
    """Get workspace status for UI."""
    return await workspace_manager.get_workspace_status(workspace_id)


@router.get("/{workspace_id}/tasks")
async def get_workspace_tasks(workspace_id: str):
    """Get all tasks for a workspace."""
    db = await get_db()
    tasks = await db.get_workspace_tasks(workspace_id)
    return tasks


@router.get("/{workspace_id}/replay")
async def replay_workspace(workspace_id: str):
    """Get recorded results for a workspace (replay = re-display, no re-execution)."""
    db = await get_db()
    history = await db.get_task_history_by_id(workspace_id)
    if not history:
        # Try loading from workspace table
        workspace = await workspace_manager.get_workspace(workspace_id)
        if workspace:
            return {
                "workspace_id": workspace_id,
                "goal": workspace.goal,
                "owner": workspace.owner,
                "status": workspace.status.value if hasattr(workspace.status, 'value') else workspace.status,
                "tasks": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "assigned_to": t.assigned_to,
                        "status": t.status.value if hasattr(t.status, 'value') else t.status,
                        "result": t.result,
                        "confidence": t.confidence,
                    }
                    for t in workspace.tasks
                ],
            }
        return {"error": "Workspace not found"}
    return history
