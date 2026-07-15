"""Base Worker - Specialized task executor."""

from abc import abstractmethod
from typing import Optional

from ..base import CardAgent
from ...core.models import Suit, Rank, AgentState, AgentMessage, Task
from ...brain.llm import LLM


class BaseWorker(CardAgent):
    """Base class for Worker agents.
    
    Workers perform focused jobs.
    Workers NEVER talk to the user.
    Workers report to Kings.
    
    Every worker should have a specialization.
    """
    
    def __init__(self, suit: Suit, rank: Rank):
        super().__init__(suit=suit, rank=rank)
        self._llm = LLM()
    
    @property
    def role(self):
        from ...core.models import AgentRole
        return AgentRole.WORKER
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this worker's specialization."""
        pass
    
    async def execute_task(self, task: Task) -> AgentMessage:
        """Execute a task and return result with confidence."""
        self.set_state(AgentState.WORKING)
        
        try:
            # Get specialized system prompt
            system_prompt = self.get_system_prompt()
            
            # Execute via LLM
            response = self._llm.chat(
                message=f"Task: {task.name}\n\nDescription: {task.description}",
                system_prompt=system_prompt,
            )
            
            # Assess confidence
            confidence = await self._assess_confidence(task, response)
            
            # Identify issues
            issues = await self._identify_issues(task, response)
            
            self.set_state(AgentState.COMPLETED)
            
            return AgentMessage(
                sender=self.card_id,
                receiver="K",  # Reports to King
                task_id=task.id,
                content=response,
                status="completed",
                confidence=confidence,
                issues=issues,
            )
        
        except Exception as e:
            self.set_state(AgentState.ERROR)
            return AgentMessage(
                sender=self.card_id,
                receiver="K",
                task_id=task.id,
                content=f"Error executing task: {str(e)}",
                status="error",
                confidence=0.0,
                issues=[str(e)],
            )
    
    async def _assess_confidence(self, task: Task, response: str) -> float:
        """Assess confidence in the response."""
        system_prompt = """Assess your confidence in this work on a scale of 0.0 to 1.0.
Consider: completeness, accuracy, potential issues, limitations.
Respond with just the number."""
        
        try:
            result = self._llm.chat(
                message=f"Task: {task.name}\nResponse: {response[:500]}",
                system_prompt=system_prompt,
                temperature=0.1,
            )
            confidence = float(result.strip())
            return max(0.0, min(1.0, confidence))
        except (ValueError, Exception):
            return 0.8  # Default confidence
    
    async def _identify_issues(self, task: Task, response: str) -> list[str]:
        """Identify potential issues with the response."""
        system_prompt = """Identify any potential issues, limitations, or concerns with this work.
List each issue on a new line, or respond with "None" if there are no issues."""
        
        try:
            result = self._llm.chat(
                message=f"Task: {task.name}\nResponse: {response[:500]}",
                system_prompt=system_prompt,
                temperature=0.1,
            )
            
            if result.strip().lower() == "none":
                return []
            
            return [line.strip() for line in result.strip().split("\n") if line.strip()]
        
        except Exception:
            return []
    
    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Workers don't process messages - they just execute tasks."""
        return None
