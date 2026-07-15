"""JARVIS - Chief Executive AI Agent."""

from typing import Optional
import json

from .base import BaseAgent
from ..core.models import AgentRole, AgentState, AgentMessage, Task
from ..brain.llm import LLM


class JarvisAgent(BaseAgent):
    """JARVIS - The Chief Executive AI.
    
    JARVIS is the single point of contact for the user.
    JARVIS understands intent, plans, delegates to Kings,
    combines results, and speaks naturally.
    
    JARVIS never directly performs specialized work.
    JARVIS delegates.
    """
    
    def __init__(self):
        super().__init__()
        self._llm = LLM()
        self._kings: dict[str, BaseAgent] = {}
    
    @property
    def card_id(self) -> str:
        return "J"
    
    @property
    def name(self) -> str:
        return "JARVIS"
    
    @property
    def role(self) -> AgentRole:
        return AgentRole.JARVIS
    
    @property
    def title(self) -> str:
        return "Chief Executive AI"
    
    @property
    def personality(self) -> str:
        return (
            "Professional, efficient, slightly witty. "
            "Proactive in suggesting solutions. "
            "Clear and concise in communication."
        )
    
    def register_king(self, king: BaseAgent):
        """Register a King agent under JARVIS."""
        self._kings[king.card_id] = king
    
    def get_king(self, card_id: str) -> Optional[BaseAgent]:
        """Get a registered King by card_id."""
        return self._kings.get(card_id)
    
    def get_all_kings(self) -> list[BaseAgent]:
        """Get all registered Kings."""
        return list(self._kings.values())
    
    async def process_user_request(self, user_message: str) -> str:
        """Main entry point: process a user request and return response."""
        self.set_state(AgentState.THINKING)
        
        # Check if LLM is available
        try:
            self._llm._get_client()
        except RuntimeError:
            # No LLM available - provide fallback response
            self.set_state(AgentState.IDLE)
            return self._fallback_response(user_message)
        
        # Analyze intent and determine which King(s) to delegate to
        delegation_plan = await self._analyze_intent(user_message)
        
        if delegation_plan.get("direct_response"):
            self.set_state(AgentState.IDLE)
            return delegation_plan["response"]
        
        # Delegate to appropriate King(s)
        results = []
        for task in delegation_plan.get("tasks", []):
            king_card = task.get("king", "♠K")
            king = self._kings.get(king_card)
            
            if king is None:
                results.append(f"No King found for {king_card}")
                continue
            
            # Create task and delegate
            task_obj = Task(
                name=task.get("name", "User request"),
                description=task.get("description", user_message),
                assigned_to=king_card,
                priority=task.get("priority", 5),
            )
            
            self.set_state(AgentState.WORKING)
            result = await king.execute_task(task_obj)
            results.append(result.content)
        
        self.set_state(AgentState.IDLE)
        
        # Combine results into natural response
        if results:
            combined = "\n\n".join(results)
            response = await self._compose_response(user_message, combined)
            return response
        
        return "I've processed your request. How else can I help?"
    
    def _fallback_response(self, user_message: str) -> str:
        """Provide a fallback response when no LLM is available."""
        msg_lower = user_message.lower().strip()
        
        # Greetings
        if any(w in msg_lower for w in ["hello", "hi", "hey", "greetings"]):
            return (
                "Hello! I'm JARVIS, your AI operating system.\n\n"
                "I'm currently running in **demo mode** because no LLM backend is configured.\n\n"
                "To enable full AI capabilities, configure one of:\n"
                "- `NVIDIA_API_KEY` in `.env`\n"
                "- [Ollama](https://ollama.com) installed locally\n\n"
                "My agent hierarchy is active and ready:\n"
                "- ♠ Engineering King + 8 workers\n"
                "- ♥ Personal King + 4 workers\n"
                "- ♦ Research King + 3 workers\n"
                "- ♣ System King + 3 workers"
            )
        
        # Status
        if any(w in msg_lower for w in ["status", "who are you", "what are you"]):
            kings_status = "\n".join(
                f"- **{king.name}** ({king.card_id}): {king.state.value}"
                for king in self._kings.values()
            )
            return (
                f"**JARVIS v2.0.0** - Multi-Agent AI Operating System\n\n"
                f"**Status:** {self.state.value}\n"
                f"**Registered Kings:** {len(self._kings)}\n\n"
                f"{kings_status}\n\n"
                f"Total workers: {sum(len(k.get_all_workers()) for k in self._kings.values())}"
            )
        
        # Help
        if any(w in msg_lower for w in ["help", "what can you do"]):
            return (
                "I'm JARVIS, and I can help you with:\n\n"
                "**Engineering** (♠): Software development, coding, architecture, testing\n"
                "**Personal** (♥): Calendar, email, tasks, scheduling\n"
                "**Research** (♦): Web research, documentation, fact-checking\n"
                "**System** (♣): File management, terminal commands, system admin\n\n"
                "Configure an LLM backend to unlock my full capabilities."
            )
        
        # Default
        return (
            f"I received your message: *\"{user_message}\"*\n\n"
            "I'm running in **demo mode** without an LLM backend.\n"
            "Configure `NVIDIA_API_KEY` or install Ollama for full AI responses."
        )
    
    async def _analyze_intent(self, message: str) -> dict:
        """Use LLM to analyze user intent and create delegation plan."""
        system_prompt = """You are JARVIS, an AI operating system. Analyze the user's request and determine how to handle it.

Available Kings:
- ♠K (Engineering King): Software development, coding, architecture, testing
- ♥K (Personal King): Calendar, email, tasks, scheduling, personal organization
- ♦K (Research King): Web research, documentation, fact-checking, analysis
- ♣K (System King): File management, terminal commands, system administration, security

Respond with JSON:
{
    "intent": "brief description of what user wants",
    "tasks": [
        {
            "king": "♠K",
            "name": "task name",
            "description": "detailed description",
            "priority": 5
        }
    ],
    "direct_response": false,
    "response": ""
}

If the request is simple conversation (greetings, questions about JARVIS, etc.), set direct_response to true and provide a response.
If the request needs work, set direct_response to false and list the tasks for the appropriate King(s)."""
        
        response = self._llm.chat_json(
            message=f"User request: {message}",
            system_prompt=system_prompt,
        )
        
        return response
    
    async def _compose_response(self, user_message: str, agent_results: str) -> str:
        """Compose a natural response from agent results."""
        system_prompt = """You are JARVIS. Compose a natural, helpful response based on the work completed by your agents.
Be professional, concise, and helpful. Include relevant details from the agent work."""
        
        response = self._llm.chat(
            message=f"User asked: {user_message}\n\nAgent results:\n{agent_results}",
            system_prompt=system_prompt,
        )
        
        return response
    
    def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process messages from Kings."""
        self._message_history.append(message)
        
        # Kings report results back to JARVIS
        if message.status == "completed":
            return AgentMessage(
                sender=self.card_id,
                receiver="user",
                task_id=message.task_id,
                content=f"Task completed: {message.content}",
                status="completed",
                confidence=message.confidence,
            )
        
        return None
    
    async def execute_task(self, task: Task) -> AgentMessage:
        """JARVIS doesn't execute tasks directly - it delegates."""
        return AgentMessage(
            sender=self.card_id,
            receiver=task.assigned_to,
            task_id=task.id,
            content="Delegated to appropriate King",
            status="delegated",
        )
    
    def get_status(self) -> dict:
        """Get JARVIS status including all registered Kings."""
        return {
            "card_id": self.card_id,
            "name": self.name,
            "state": self.state.value,
            "kings": {
                king.card_id: king.to_dict()
                for king in self._kings.values()
            },
        }
