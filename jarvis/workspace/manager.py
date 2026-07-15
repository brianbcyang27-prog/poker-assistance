"""Workspace Manager - Mission tracking and coordination."""

from typing import Optional
from datetime import datetime

from ..core.models import Workspace, Task, AgentState
from ..core.database import get_db


class WorkspaceManager:
    """Manages workspaces for tracking missions."""
    
    def __init__(self):
        self._active_workspaces: dict[str, Workspace] = {}
    
    async def create_workspace(self, goal: str, owner: str) -> Workspace:
        """Create a new workspace for a mission."""
        workspace = Workspace(goal=goal, owner=owner)
        self._active_workspaces[workspace.id] = workspace
        
        # Persist to database
        db = await get_db()
        await db.save_workspace(workspace.model_dump())
        
        return workspace
    
    async def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID."""
        # Check in-memory first
        if workspace_id in self._active_workspaces:
            return self._active_workspaces[workspace_id]
        
        # Check database
        db = await get_db()
        data = await db.get_workspace(workspace_id)
        if data:
            workspace = Workspace(**data)
            self._active_workspaces[workspace_id] = workspace
            return workspace
        
        return None
    
    async def get_active_workspaces(self) -> list[Workspace]:
        """Get all active workspaces."""
        db = await get_db()
        data = await db.get_all_workspaces(status="working")
        return [Workspace(**d) for d in data]
    
    async def add_task(self, workspace_id: str, task: Task) -> bool:
        """Add a task to a workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False
        
        workspace.tasks.append(task)
        
        # Persist
        db = await get_db()
        await db.save_task(task.model_dump(), workspace_id)
        await db.save_workspace(workspace.model_dump())
        
        return True
    
    async def update_task_status(
        self,
        workspace_id: str,
        task_id: str,
        status: AgentState,
        result: Optional[str] = None,
        confidence: float = 0.0,
        issues: Optional[list[str]] = None,
    ) -> bool:
        """Update a task's status."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False
        
        for task in workspace.tasks:
            if task.id == task_id:
                task.status = status
                task.result = result
                task.confidence = confidence
                task.issues = issues or []
                if status in (AgentState.COMPLETED, AgentState.ERROR):
                    task.completed_at = datetime.now()
                break
        
        workspace.update_progress()
        
        # Persist
        db = await get_db()
        for task in workspace.tasks:
            if task.id == task_id:
                await db.save_task(task.model_dump(), workspace_id)
                break
        await db.save_workspace(workspace.model_dump())
        
        return True
    
    async def complete_workspace(self, workspace_id: str) -> bool:
        """Mark a workspace as completed."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False
        
        workspace.status = AgentState.COMPLETED
        workspace.progress = 100.0
        workspace.completed_at = datetime.now()
        
        # Persist
        db = await get_db()
        await db.save_workspace(workspace.model_dump())
        
        # Move to completed
        self._active_workspaces.pop(workspace_id, None)
        
        return True
    
    def get_workspace_status(self, workspace_id: str) -> dict:
        """Get workspace status for UI display."""
        workspace = self._active_workspaces.get(workspace_id)
        if not workspace:
            return {"error": "Workspace not found"}
        
        return {
            "id": workspace.id,
            "goal": workspace.goal,
            "owner": workspace.owner,
            "status": workspace.status.value,
            "progress": workspace.progress,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "assigned_to": t.assigned_to,
                    "status": t.status.value,
                    "confidence": t.confidence,
                }
                for t in workspace.tasks
            ],
        }
