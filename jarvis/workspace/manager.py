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
            # Load tasks from the tasks table
            task_data = await db.get_workspace_tasks(workspace_id)
            tasks = []
            for td in task_data:
                tasks.append(Task(
                    id=td["id"],
                    name=td["name"],
                    description=td["description"],
                    assigned_to=td["assigned_to"],
                    status=td["status"],
                    priority=td["priority"],
                    dependencies=td.get("dependencies", []),
                    result=td.get("result"),
                    confidence=td.get("confidence", 0.0),
                    issues=td.get("issues", []),
                    created_at=td.get("created_at"),
                    completed_at=td.get("completed_at"),
                ))
            
            workspace = Workspace(
                id=data["id"],
                goal=data["goal"],
                owner=data["owner"],
                status=data["status"],
                progress=data.get("progress", 0.0),
                tasks=tasks,
                created_at=data.get("created_at"),
                completed_at=data.get("completed_at"),
            )
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
        """Mark a workspace as completed and save to history."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False
        
        workspace.status = AgentState.COMPLETED
        workspace.progress = 100.0
        workspace.completed_at = datetime.now()
        
        # Persist
        db = await get_db()
        await db.save_workspace(workspace.model_dump())
        
        # Save to task history for the history page
        duration_ms = None
        if workspace.created_at and workspace.completed_at:
            try:
                from datetime import datetime as dt
                created = dt.fromisoformat(workspace.created_at) if isinstance(workspace.created_at, str) else workspace.created_at
                completed = dt.fromisoformat(workspace.completed_at) if isinstance(workspace.completed_at, str) else workspace.completed_at
                duration_ms = int((completed - created).total_seconds() * 1000)
            except Exception:
                pass
        
        await db.save_task_history({
            "plan_id": workspace_id,
            "user_request": workspace.goal,
            "summary": f"Workspace completed: {workspace.goal}",
            "tasks": [t.model_dump() for t in workspace.tasks],
            "workspace_id": workspace_id,
            "owner": workspace.owner,
            "duration_ms": duration_ms,
        })
        
        # Move to completed
        self._active_workspaces.pop(workspace_id, None)
        
        return True
    
    async def get_workspace_status(self, workspace_id: str) -> dict:
        """Get workspace status for UI display."""
        # Try in-memory first, then database
        workspace = self._active_workspaces.get(workspace_id)
        if not workspace:
            workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return {"error": "Workspace not found"}
        
        return {
            "id": workspace.id,
            "goal": workspace.goal,
            "owner": workspace.owner,
            "status": workspace.status.value if hasattr(workspace.status, 'value') else workspace.status,
            "progress": workspace.progress,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "assigned_to": t.assigned_to,
                    "status": t.status.value if hasattr(t.status, 'value') else t.status,
                    "confidence": t.confidence,
                }
                for t in workspace.tasks
            ],
        }
