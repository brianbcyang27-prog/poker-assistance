"""Workspace Manager — unified mission tracking and coordination (v6.1.0)."""

import json
from typing import Optional
from datetime import datetime

from ..core.models import Workspace, Task, AgentState
from ..core.database import get_db


class WorkspaceManager:
    """Manages unified mission workspaces."""

    def __init__(self):
        self._active_workspaces: dict[str, Workspace] = {}

    async def create_workspace(
        self,
        goal: str,
        owner: str,
        user_request: str = "",
        priority: str = "normal",
    ) -> Workspace:
        """Create a new workspace for a mission."""
        ws = Workspace(
            goal=goal,
            owner=owner,
            user_request=user_request or goal,
            priority=priority,
        )
        ws.started_at = datetime.now()
        self._active_workspaces[ws.id] = ws

        db = await get_db()
        await db.save_workspace(ws.model_dump())
        return ws

    async def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """Get a workspace by ID."""
        if workspace_id in self._active_workspaces:
            return self._active_workspaces[workspace_id]

        db = await get_db()
        data = await db.get_workspace(workspace_id)
        if not data:
            return None

        task_data = await db.get_workspace_tasks(workspace_id)
        tasks = []
        for td in task_data:
            deps = td.get("dependencies", "[]")
            if isinstance(deps, str):
                try:
                    deps = json.loads(deps)
                except (json.JSONDecodeError, TypeError):
                    deps = []
            issues = td.get("issues", "[]")
            if isinstance(issues, str):
                try:
                    issues = json.loads(issues)
                except (json.JSONDecodeError, TypeError):
                    issues = []
            tasks.append(Task(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                assigned_to=td["assigned_to"],
                status=td["status"],
                priority=td["priority"],
                dependencies=deps,
                result=td.get("result"),
                confidence=td.get("confidence", 0.0),
                issues=issues,
                created_at=td.get("created_at"),
                completed_at=td.get("completed_at"),
            ))

        ws = Workspace(
            id=data["id"],
            goal=data["goal"],
            owner=data["owner"],
            user_request=data.get("user_request", ""),
            tasks=tasks,
            status=data["status"],
            current_stage=data.get("current_stage", "understand"),
            progress=data.get("progress", 0.0),
            priority=data.get("priority", "normal"),
            created_at=data.get("created_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_ms=data.get("duration_ms", 0.0),
            research_findings=data.get("research_findings", []),
            tool_candidates=data.get("tool_candidates", []),
            architecture_plan=data.get("architecture_plan"),
            execution_results=data.get("execution_results", []),
            verification_results=data.get("verification_results", []),
            review_items=data.get("review_items", []),
            memory_record=data.get("memory_record"),
            final_report=data.get("final_report", ""),
            timeline_events=data.get("timeline_events", []),
            stage_history=data.get("stage_history", []),
            errors=data.get("errors", []),
        )
        self._active_workspaces[workspace_id] = ws
        return ws

    async def get_active_workspaces(self) -> list[Workspace]:
        """Get all active workspaces (planning, working, reviewing)."""
        db = await get_db()
        active_statuses = ["planning", "working", "reviewing", "created",
                           "researching", "executing", "verifying", "paused"]
        results = []
        for st in active_statuses:
            data = await db.get_all_workspaces(status=st, limit=50)
            for d in data:
                if d["id"] not in self._active_workspaces:
                    ws = await self.get_workspace(d["id"])
                    if ws:
                        results.append(ws)
        results.extend(self._active_workspaces.values())
        return results

    async def add_task(self, workspace_id: str, task: Task) -> bool:
        """Add a task to a workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False

        workspace.tasks.append(task)
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
        db = await get_db()
        for task in workspace.tasks:
            if task.id == task_id:
                await db.save_task(task.model_dump(), workspace_id)
                break
        await db.save_workspace(workspace.model_dump())
        return True

    async def add_timeline_event(
        self,
        workspace_id: str,
        event_type: str,
        source: str,
        description: str,
        **extra,
    ) -> bool:
        """Add a timeline event to a workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False

        workspace.add_timeline_event(event_type, source, description, **extra)
        db = await get_db()
        await db.save_workspace(workspace.model_dump())
        return True

    async def record_stage(
        self,
        workspace_id: str,
        stage: str,
        action: str = "start",
    ) -> bool:
        """Record a pipeline stage transition."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False

        if action == "start":
            workspace.stage_start(stage)
        else:
            workspace.stage_complete(stage)

        db = await get_db()
        await db.save_workspace(workspace.model_dump())
        return True

    async def add_error(self, workspace_id: str, error: str) -> bool:
        """Add an error to a workspace."""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False

        workspace.add_error(error)
        db = await get_db()
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

        if workspace.started_at:
            try:
                started = workspace.started_at if isinstance(workspace.started_at, datetime) else datetime.fromisoformat(str(workspace.started_at))
                workspace.duration_ms = (datetime.now() - started).total_seconds() * 1000
            except Exception:
                pass

        db = await get_db()
        await db.save_workspace(workspace.model_dump())

        await db.save_task_history({
            "plan_id": workspace_id,
            "user_request": workspace.user_request or workspace.goal,
            "summary": f"Workspace completed: {workspace.goal}",
            "tasks_json": json.dumps([t.model_dump() for t in workspace.tasks]),
            "workspace_id": workspace_id,
            "owner": workspace.owner,
            "duration_ms": int(workspace.duration_ms),
        })

        self._active_workspaces.pop(workspace_id, None)
        return True

    async def get_workspace_status(self, workspace_id: str) -> dict:
        """Get workspace status for UI display."""
        workspace = self._active_workspaces.get(workspace_id)
        if not workspace:
            workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return {"error": "Workspace not found"}

        status_val = workspace.status.value if hasattr(workspace.status, "value") else workspace.status
        return {
            "id": workspace.id,
            "goal": workspace.goal,
            "owner": workspace.owner,
            "user_request": workspace.user_request,
            "status": status_val,
            "current_stage": workspace.current_stage,
            "progress": workspace.progress,
            "priority": workspace.priority,
            "tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "assigned_to": t.assigned_to,
                    "status": t.status.value if hasattr(t.status, "value") else t.status,
                    "confidence": t.confidence,
                    "dependencies": t.dependencies,
                }
                for t in workspace.tasks
            ],
            "timeline_count": len(workspace.timeline_events),
            "error_count": len(workspace.errors),
            "stage": workspace.current_stage,
        }

    async def search_workspaces(self, query: str, limit: int = 20) -> list[dict]:
        """Search workspaces by goal or user_request."""
        db = await get_db()
        all_ws = await db.get_all_workspaces(limit=200)
        query_lower = query.lower()
        results = []
        for d in all_ws:
            if (query_lower in (d.get("goal", "") + " " + d.get("user_request", "")).lower()):
                results.append({
                    "id": d["id"],
                    "goal": d["goal"],
                    "status": d["status"],
                    "created_at": d.get("created_at"),
                })
                if len(results) >= limit:
                    break
        return results
