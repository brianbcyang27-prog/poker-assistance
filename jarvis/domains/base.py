"""Domain member base classes — v10 parallel hierarchy to the card agents.

Domain members use `member_id` identities (e.g. "education.tutor").
`card_id` remains available as a compat alias so existing tooling that keys
on card_id keeps working (§3.1 compat-first).
"""

import asyncio
import logging
from abc import abstractmethod

from ..agents.base import BaseAgent
from ..brain.llm import LLM
from ..core.models import AgentMessage, AgentRole, AgentState, Task
from .models import Domain

logger = logging.getLogger(__name__)


def member_id_of(member) -> str:
    """Return a member's id, tolerating both card agents and domain members."""
    value = getattr(member, "member_id", None) or getattr(member, "card_id", None)
    return str(value)


class DomainMember(BaseAgent):
    """A member of a domain (master or worker), identified by member_id."""

    def __init__(self, domain: Domain, member_id: str, role: AgentRole):
        super().__init__()
        self._domain = domain
        self._member_id = member_id
        self._role = role
        self._llm = None

    @property
    def member_id(self) -> str:
        return self._member_id

    @property
    def card_id(self) -> str:
        return self._member_id

    @property
    def domain(self) -> Domain:
        return self._domain

    @property
    def role(self) -> AgentRole:
        return self._role

    @property
    def is_master(self) -> bool:
        return self._role is AgentRole.KING

    @property
    def name(self) -> str:
        return self._member_id

    @property
    def title(self) -> str:
        return f"{self._domain.label} {self._role.value.title()}"

    def get_model_config(self) -> dict:
        """Override to use a different LLM for this member (model/api_base/api_key)."""
        return {}

    def _get_llm(self) -> LLM:
        if self._llm is None:
            config = self.get_model_config()
            self._llm = LLM(
                model=config.get("model"),
                api_base=config.get("api_base"),
                api_key=config.get("api_key"),
            )
        return self._llm

    def process_message(self, message: AgentMessage) -> AgentMessage | None:
        self._message_history.append(message)
        return None

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["member_id"] = self._member_id
        data["domain"] = self._domain.value
        data["card_id"] = self._member_id
        return data


class DomainWorker(DomainMember):
    """LLM-driven domain worker — the v10 counterpart of the card Workers.

    Tool integration is intentionally deferred to the Global Pipeline (M2);
    M1 focuses on the domain model and execution contract.
    """

    def __init__(self, domain: Domain, member_id: str):
        super().__init__(domain, member_id, AgentRole.WORKER)

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    async def execute_task(self, task: Task, peer_context: str = "") -> AgentMessage:
        from ..core.events import Event, event_bus

        self.set_state(AgentState.WORKING)
        await event_bus.emit(
            Event(
                type="worker.started",
                data={"worker": self.member_id, "task": task.name},
                source=self.member_id,
            )
        )

        try:
            message = f"Task: {task.name}\n\nDescription: {task.description}"
            if peer_context:
                message += f"\n\n=== Results from other workers ===\n{peer_context}"

            response = await asyncio.to_thread(
                self._get_llm().chat,
                message=message,
                system_prompt=self.get_system_prompt(),
            )
            confidence = await self._assess_confidence(task, response)
            issues = await self._identify_issues(task, response)

            try:
                from ..brain.review import review_pipeline

                review = await review_pipeline.review(
                    task_type=task.name,
                    task_description=task.description,
                    result=response,
                    confidence=confidence,
                    issues=issues,
                )
                issues = list(set(issues + review.issues))
            except Exception:
                review = None

            self.set_state(AgentState.COMPLETED)
            await event_bus.emit(
                Event(
                    type="worker.completed",
                    data={
                        "worker": self.member_id,
                        "task": task.name,
                        "confidence": confidence,
                        "issues": issues,
                        "review": review.to_dict() if review else None,
                    },
                    source=self.member_id,
                )
            )
            return AgentMessage(
                sender=self.member_id,
                receiver=self.domain.master_member_id,
                task_id=task.id,
                content=response,
                status="completed",
                confidence=confidence,
                issues=issues,
            )
        except Exception as e:
            self.set_state(AgentState.ERROR)
            await event_bus.emit(
                Event(
                    type="worker.error",
                    data={"worker": self.member_id, "task": task.name, "error": str(e)},
                    source=self.member_id,
                )
            )
            return AgentMessage(
                sender=self.member_id,
                receiver=self.domain.master_member_id,
                task_id=task.id,
                content=f"Error executing task: {str(e)}",
                status="error",
                confidence=0.0,
                issues=[str(e)],
            )

    async def _assess_confidence(self, task: Task, response: str) -> float:
        system_prompt = (
            "Assess your confidence in this work on a scale of 0.0 to 1.0. "
            "Consider: completeness, accuracy, potential issues, limitations. "
            "Respond with just the number."
        )
        try:
            result = await asyncio.to_thread(
                self._get_llm().chat,
                message=f"Task: {task.name}\nResponse: {response[:500]}",
                system_prompt=system_prompt,
                temperature=0.1,
            )
            return max(0.0, min(1.0, float(result.strip())))
        except Exception:
            return 0.8

    async def _identify_issues(self, task: Task, response: str) -> list[str]:
        system_prompt = (
            "Identify any potential issues, limitations, or concerns with this work. "
            "List each issue on a new line, or respond with None if there are none."
        )
        try:
            result = await asyncio.to_thread(
                self._get_llm().chat,
                message=f"Task: {task.name}\nResponse: {response[:500]}",
                system_prompt=system_prompt,
                temperature=0.1,
            )
            if result.strip().lower() == "none":
                return []
            return [line.strip() for line in result.strip().split("\n") if line.strip()]
        except Exception:
            return []


class DomainMaster(DomainMember):
    """Domain manager — plans, delegates to members, and reviews results.

    When a domain is backed by an existing card King (engineering, research,
    personal, system), execution delegates to that King unchanged; the master
    still exposes the domain's member roster for the v10 APIs.
    """

    def __init__(self, domain: Domain, member_id: str):
        super().__init__(domain, member_id, AgentRole.KING)
        self._members: dict[str, DomainMember] = {}
        self._king = None
        self._active_tasks: dict[str, Task] = {}
        self._build_members()

    @property
    def is_king_backed(self) -> bool:
        return self._king is not None

    def _build_members(self) -> None:
        """Register this domain's canonical members. Override in subclasses."""

    def attach_king(self, king) -> None:
        """Attach the compat card King this domain delegates execution to."""
        self._king = king

    def register_member(self, member) -> None:
        """Register a member (DomainMember or card Worker) under this master."""
        self._members[member_id_of(member)] = member

    def get_member(self, member_id: str):
        return self._members.get(member_id)

    def get_all_members(self) -> list:
        return list(self._members.values())

    def get_status(self) -> dict:
        base = self.to_dict()
        base["members"] = {member_id_of(m): m.to_dict() for m in self._members.values()}
        base["active_tasks"] = len(self._active_tasks)
        base["backed_by_king"] = self._king.card_id if self._king else None
        return base

    async def execute_task(self, task: Task) -> AgentMessage:
        if self._king is not None:
            return await self._king.execute_task(task)

        if not self._members:
            return AgentMessage(
                sender=self.member_id,
                receiver="J",
                task_id=task.id,
                content=f"No workers available in domain {self.domain.value}",
                status="error",
                confidence=0.0,
                issues=["no workers"],
            )

        self.set_state(AgentState.PLANNING)
        self._active_tasks[task.id] = task
        try:
            plan = await self._plan_work(task)
            results = await self._delegate_to_members(task, plan)
            return await self._review_results(task, results)
        finally:
            self._active_tasks.pop(task.id, None)

    async def _plan_work(self, task: Task) -> dict:
        system_prompt = f"""You are the {self.name}, the {self.domain.label} domain master.

Plan how to accomplish this task. Break it down into subtasks.

Available members (use ONLY the member_id, nothing else):
{self._format_members()}

CRITICAL: The "assigned_member" field MUST be exactly the member_id \
(e.g. "{self.domain.value}.tutor"). Do NOT include member names, titles, \
or descriptions in the assigned_member field. Just the member_id.

Respond with JSON:
{{
    "subtasks": [
        {{
            "name": "subtask name",
            "description": "what needs to be done",
            "assigned_member": "{self.domain.value}.tutor",
            "priority": 5
        }}
    ],
    "estimated_time": "estimated time",
    "notes": "any planning notes"
}}"""

        response = self._get_llm().chat_json(
            message=f"Task: {task.name}\nDescription: {task.description}",
            system_prompt=system_prompt,
        )

        if response.get("parse_error") or "subtasks" not in response:
            logger.warning(
                "Domain plan parse failed (%s): %s",
                self.domain.value,
                response.get("raw_response", "")[:200],
            )
            members = self.get_all_members()
            if members:
                response = {
                    "subtasks": [
                        {
                            "name": task.name,
                            "description": task.description,
                            "assigned_member": member_id_of(members[0]),
                            "priority": 5,
                        }
                    ],
                    "estimated_time": "unknown",
                    "notes": "Auto-assigned (LLM plan parse failed)",
                }
        return response

    def _resolve_member(self, member_id: str):
        exact = self._members.get(member_id)
        if exact:
            return exact
        lowered = member_id.lower()
        for mid, member in self._members.items():
            if getattr(member, "name", "").lower() in lowered:
                return member
        return None

    async def _delegate_to_members(self, task: Task, plan: dict) -> list[AgentMessage]:
        results = []
        completed_context = []
        for subtask in plan.get("subtasks", []):
            member_id = subtask.get("assigned_member", "")
            member = self._resolve_member(member_id)
            if member is None:
                results.append(
                    AgentMessage(
                        sender=self.member_id,
                        receiver=member_id,
                        task_id=task.id,
                        content=f"Member {member_id} not found",
                        status="error",
                    )
                )
                continue

            subtask_obj = Task(
                name=subtask.get("name", "Subtask"),
                description=subtask.get("description", ""),
                assigned_to=member_id,
                priority=subtask.get("priority", 5),
                dependencies=subtask.get("dependencies", []),
            )

            peer_context = ""
            if completed_context:
                peer_context = "\n".join(
                    f"Member {r.sender} completed '{r.task_id}': {r.content[:300]}"
                    for r in completed_context[-3:]
                )

            result = await member.execute_task(subtask_obj, peer_context=peer_context)
            results.append(result)
            if result.status == "completed":
                completed_context.append(result)
        return results

    async def _review_results(self, task: Task, results: list[AgentMessage]) -> AgentMessage:
        if not results:
            return AgentMessage(
                sender=self.member_id,
                receiver="J",
                task_id=task.id,
                content="No results to review",
                status="error",
                confidence=0.0,
            )

        avg_confidence = sum(r.confidence for r in results) / len(results)
        all_issues = [issue for r in results for issue in r.issues]
        threshold = self._config.confidence_threshold

        if avg_confidence >= threshold and not all_issues:
            summary = "\n".join(f"[{r.sender}] {r.content}" for r in results)
            return AgentMessage(
                sender=self.member_id,
                receiver="J",
                task_id=task.id,
                content=summary,
                status="completed",
                confidence=avg_confidence,
            )
        return AgentMessage(
            sender=self.member_id,
            receiver="J",
            task_id=task.id,
            content=f"Task completed with concerns. Confidence: {avg_confidence:.0%}",
            status="needs_revision",
            confidence=avg_confidence,
            issues=all_issues,
        )

    def _format_members(self) -> str:
        lines = [f"- {member_id_of(m)}" for m in self._members.values()]
        return "\n".join(lines) if lines else "No members registered"
