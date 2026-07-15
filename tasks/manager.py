from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime
import uuid


class TaskType(str, Enum):
    CODE = "code"
    DOCUMENT = "document"
    TEST = "test"
    DEPLOY = "deploy"
    RESEARCH = "research"


class TaskPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class Task(BaseModel):
    """Represents a single task."""
    id: str
    name: str
    description: str
    type: TaskType
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    agent: str = "opencode"
    dependencies: list[str] = []
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None


class TaskPlan(BaseModel):
    """Represents a complete task plan."""
    id: str
    user_request: str
    tasks: list[Task] = []
    summary: str = ""
    estimated_total: str = ""
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None


class TaskManager:
    """Manages task creation, tracking, and execution."""
    
    def __init__(self):
        self.active_plans: dict[str, TaskPlan] = {}
        self.completed_plans: list[TaskPlan] = []
    
    def create_plan_from_llm(
        self,
        user_request: str,
        llm_response: dict,
    ) -> TaskPlan:
        """Create a task plan from LLM response."""
        plan = TaskPlan(
            id=str(uuid.uuid4())[:8],
            user_request=user_request,
            summary=llm_response.get("summary", ""),
            estimated_total=llm_response.get("estimated_total", "Unknown"),
        )
        
        for task_data in llm_response.get("tasks", []):
            task = Task(
                id=str(task_data.get("id", uuid.uuid4().hex[:4])),
                name=task_data.get("name", "Unnamed Task"),
                description=task_data.get("description", ""),
                type=TaskType(task_data.get("type", "code")),
                priority=TaskPriority(task_data.get("priority", "medium")),
                agent=task_data.get("agent", "opencode"),
                dependencies=task_data.get("dependencies", []),
            )
            plan.tasks.append(task)
        
        self.active_plans[plan.id] = plan
        return plan
    
    def create_plan(
        self,
        user_request: str,
        tasks: list[dict],
        summary: str = "",
        estimated_total: str = "",
    ) -> TaskPlan:
        """Create a task plan directly."""
        plan = TaskPlan(
            id=str(uuid.uuid4())[:8],
            user_request=user_request,
            summary=summary,
            estimated_total=estimated_total,
        )
        
        for task_data in tasks:
            task = Task(
                id=str(task_data.get("id", uuid.uuid4().hex[:4])),
                name=task_data.get("name", "Unnamed Task"),
                description=task_data.get("description", ""),
                type=TaskType(task_data.get("type", "code")),
                priority=TaskPriority(task_data.get("priority", "medium")),
                agent=task_data.get("agent", "opencode"),
                dependencies=task_data.get("dependencies", []),
            )
            plan.tasks.append(task)
        
        self.active_plans[plan.id] = plan
        return plan
    
    def get_next_tasks(self, plan_id: str) -> list[Task]:
        """Get tasks that can be executed now (dependencies satisfied)."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return []
        
        completed_ids = {
            t.id for t in plan.tasks if t.status == TaskStatus.COMPLETED
        }
        
        ready_tasks = []
        for task in plan.tasks:
            if task.status != TaskStatus.PENDING:
                continue
            
            deps_met = all(dep in completed_ids for dep in task.dependencies)
            if deps_met:
                ready_tasks.append(task)
        
        return ready_tasks
    
    def update_task_status(
        self,
        plan_id: str,
        task_id: str,
        status: TaskStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Update a task's status."""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
        
        for task in plan.tasks:
            if task.id == task_id:
                task.status = status
                task.result = result
                task.error = error
                if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                    task.completed_at = datetime.now()
                break
        
        if all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for t in plan.tasks
        ):
            plan.completed_at = datetime.now()
            self.completed_plans.append(plan)
            del self.active_plans[plan_id]
    
    def format_plan(self, plan: TaskPlan) -> str:
        """Format a task plan for display."""
        lines = [
            f"📋 Task Plan: {plan.id}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📝 Request: {plan.user_request}",
            f"💬 Summary: {plan.summary}",
            f"⏱️  Estimated: {plan.estimated_total}",
            f"",
            "Tasks:",
        ]
        
        for task in plan.tasks:
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.BLOCKED: "🚫",
            }.get(task.status, "❓")
            
            priority_icon = {
                TaskPriority.HIGH: "🔴",
                TaskPriority.MEDIUM: "🟡",
                TaskPriority.LOW: "🟢",
            }.get(task.priority, "⚪")
            
            lines.append(
                f"  {status_icon} {priority_icon} [{task.id}] {task.name}"
            )
            lines.append(f"      {task.description}")
            lines.append(f"      Agent: {task.agent} | Type: {task.type.value}")
            if task.dependencies:
                lines.append(f"      Depends on: {', '.join(task.dependencies)}")
            lines.append("")
        
        return "\n".join(lines)