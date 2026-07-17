"""Base King - Division manager base class."""

from abc import abstractmethod
from typing import Optional
import json

from ..base import CardAgent
from ...core.models import (
    Suit, Rank, AgentRole, AgentState, AgentMessage, Task
)
from ...brain.llm import LLM


class BaseKing(CardAgent):
    """Base class for King agents.
    
    Kings are managers. They own outcomes.
    Kings do NOT spend most of their time writing code.
    
    Responsibilities:
    - Planning
    - Assigning work
    - Selecting worker cards
    - Reviewing quality
    - Requesting revisions
    - Approving completion
    - Reporting to JARVIS
    """
    
    def __init__(self, suit: Suit):
        super().__init__(suit=suit, rank=Rank.KING)
        config = self.get_model_config()
        self._llm = LLM(
            model=config.get("model"),
            api_base=config.get("api_base"),
            api_key=config.get("api_key"),
        )
        self._workers: dict[str, CardAgent] = {}
        self._active_tasks: dict[str, Task] = {}
    
    def get_model_config(self) -> dict:
        """Override to use a different LLM for this king.
        
        Returns dict with optional keys: model, api_base, api_key
        Example: {"model": "meta/llama-3.1-70b-instruct"}
        """
        return {}
    
    @property
    def role(self) -> AgentRole:
        return AgentRole.KING
    
    @property
    def is_king(self) -> bool:
        return True
    
    def register_worker(self, worker: CardAgent):
        """Register a worker card under this King."""
        self._workers[worker.card_id] = worker
    
    def get_worker(self, card_id: str) -> Optional[CardAgent]:
        """Get a registered worker by card_id."""
        return self._workers.get(card_id)
    
    def get_all_workers(self) -> list[CardAgent]:
        """Get all registered workers."""
        return list(self._workers.values())
    
    def get_workers_by_rank(self, rank: Rank) -> list[CardAgent]:
        """Get workers of a specific rank."""
        return [w for w in self._workers.values() if w.rank == rank]
    
    async def execute_task(self, task: Task) -> AgentMessage:
        """Execute a task by planning, delegating, and reviewing."""
        self.set_state(AgentState.PLANNING)
        self._active_tasks[task.id] = task

        # v3.1: Emit event
        from ...core.events import event_bus, Event
        await event_bus.emit(Event(
            type="king.planning",
            data={"king": self.card_id, "task": task.name},
            source=self.card_id,
        ))
        
        # Step 1: Plan the work
        plan = await self._plan_work(task)
        
        # Step 2: Assemble team
        team = self._assemble_team(plan)

        # v3.1: Emit delegation event
        await event_bus.emit(Event(
            type="king.delegated",
            data={
                "king": self.card_id,
                "task": task.name,
                "workers": [w.card_id for w in team],
                "subtasks": len(plan.get("subtasks", [])),
            },
            source=self.card_id,
        ))
        
        # Step 3: Delegate to workers
        self.set_state(AgentState.WORKING)
        worker_results = await self._delegate_to_workers(task, plan, team)
        
        # Step 4: Review quality
        self.set_state(AgentState.REVIEWING)
        review = await self._review_results(task, worker_results)
        
        # Step 5: Report to JARVIS
        self.set_state(AgentState.IDLE)
        self._active_tasks.pop(task.id, None)

        # v3.1: Emit completion event
        await event_bus.emit(Event(
            type="king.completed",
            data={
                "king": self.card_id,
                "task": task.name,
                "confidence": review.confidence,
                "issues": review.issues,
            },
            source=self.card_id,
        ))
        
        return review
    
    async def _plan_work(self, task: Task) -> dict:
        """Plan how to accomplish the task."""
        system_prompt = f"""You are the {self.name}, a King agent managing {self.suit.value} work.
        
Your personality: {self.personality}

Plan how to accomplish this task. Break it down into subtasks.

Available workers:
{self._format_workers()}

Respond with JSON:
{{
    "subtasks": [
        {{
            "name": "subtask name",
            "description": "what needs to be done",
            "assigned_worker": "worker card_id (e.g., {self.suit.symbol}Q)",
            "priority": 5
        }}
    ],
    "estimated_time": "estimated time",
    "notes": "any planning notes"
}}"""
        
        response = self._llm.chat_json(
            message=f"Task: {task.name}\nDescription: {task.description}",
            system_prompt=system_prompt,
        )
        
        return response
    
    def _assemble_team(self, plan: dict) -> list[CardAgent]:
        """Assemble a team of workers based on the plan."""
        team = []
        for subtask in plan.get("subtasks", []):
            worker_id = subtask.get("assigned_worker", "")
            worker = self._workers.get(worker_id)
            if worker and worker not in team:
                team.append(worker)
        return team
    
    async def _delegate_to_workers(
        self, task: Task, plan: dict, team: list[CardAgent]
    ) -> list[AgentMessage]:
        """Delegate subtasks to workers and collect results."""
        results = []
        
        for subtask in plan.get("subtasks", []):
            worker_id = subtask.get("assigned_worker", "")
            worker = self._workers.get(worker_id)
            
            if worker is None:
                results.append(AgentMessage(
                    sender=self.card_id,
                    receiver=worker_id,
                    task_id=task.id,
                    content=f"Worker {worker_id} not found",
                    status="error",
                ))
                continue
            
            # Create subtask
            subtask_obj = Task(
                name=subtask.get("name", "Subtask"),
                description=subtask.get("description", ""),
                assigned_to=worker_id,
                priority=subtask.get("priority", 5),
            )
            
            # Worker executes
            worker.set_state(AgentState.WORKING)
            result = await worker.execute_task(subtask_obj)
            worker.set_state(AgentState.IDLE)
            
            results.append(result)
        
        return results
    
    async def _review_results(self, task: Task, results: list[AgentMessage]) -> AgentMessage:
        """Review worker results and determine if quality is acceptable."""
        # Calculate average confidence
        if not results:
            return AgentMessage(
                sender=self.card_id,
                receiver="J",
                task_id=task.id,
                content="No results to review",
                status="error",
                confidence=0.0,
            )
        
        avg_confidence = sum(r.confidence for r in results) / len(results)
        all_issues = []
        for r in results:
            all_issues.extend(r.issues)
        
        # Determine if we need revisions
        threshold = self._config.confidence_threshold
        
        if avg_confidence >= threshold and not all_issues:
            # Approved
            summary = self._compile_summary(results)
            return AgentMessage(
                sender=self.card_id,
                receiver="J",
                task_id=task.id,
                content=summary,
                status="completed",
                confidence=avg_confidence,
                issues=[],
            )
        else:
            # Needs revision
            return AgentMessage(
                sender=self.card_id,
                receiver="J",
                task_id=task.id,
                content=f"Task completed with concerns. Confidence: {avg_confidence:.0%}",
                status="needs_revision",
                confidence=avg_confidence,
                issues=all_issues,
            )
    
    def _compile_summary(self, results: list[AgentMessage]) -> str:
        """Compile worker results into a summary."""
        parts = []
        for r in results:
            parts.append(f"[{r.sender}] {r.content}")
        return "\n".join(parts)
    
    def _format_workers(self) -> str:
        """Format worker list for prompts."""
        lines = []
        for worker in self._workers.values():
            lines.append(f"- {worker.card_id}: {worker.name} - {worker.title}")
        return "\n".join(lines) if lines else "No workers registered"
    
    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process message from workers or JARVIS."""
        self._message_history.append(message)
        
        if message.status == "completed":
            # Worker completed a task
            return AgentMessage(
                sender=self.card_id,
                receiver="J",
                task_id=message.task_id,
                content=f"Worker {message.sender} completed: {message.content}",
                status="completed",
                confidence=message.confidence,
            )
        
        return None
    
    def get_status(self) -> dict:
        """Get King status including workers."""
        base = self.to_dict()
        base["workers"] = {
            w.card_id: w.to_dict() for w in self._workers.values()
        }
        base["active_tasks"] = len(self._active_tasks)
        return base
