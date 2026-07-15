"""Workspace router - Mission tracking."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from jarvis.web.main import workspace_manager, jarvis
from jarvis.core.models import Task

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class CreateWorkspaceRequest(BaseModel):
    goal: str
    owner: str = "♠K"


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
    return workspace_manager.get_workspace_status(workspace_id)
