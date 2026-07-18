"""JARVIS - Chief Executive AI Agent."""

from typing import Optional
import json

from .base import BaseAgent
from ..core.models import AgentRole, AgentState, AgentMessage, Task
from ..brain.llm import LLM
from ..brain.dag_planner import dag_planner


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

        # v3.1: Emit event
        from ..core.events import event_bus, Event
        await event_bus.emit(Event(
            type="jarvis.thinking",
            data={"message": user_message},
            source="J",
        ))
        
        # Check if LLM is available
        if not self._llm.is_available():
            self.set_state(AgentState.IDLE)
            return self._fallback_response(user_message)
        
        # Analyze intent and determine which King(s) to delegate to
        delegation_plan = await self._analyze_intent(user_message)
        self._last_intent = delegation_plan
        
        # Safety: if tasks exist, ALWAYS delegate — never fabricate a response
        tasks = delegation_plan.get("tasks", [])
        if tasks:
            delegation_plan["direct_response"] = False
            delegation_plan["response"] = ""
        
        if delegation_plan.get("direct_response"):
            self.set_state(AgentState.IDLE)
            await event_bus.emit(Event(
                type="jarvis.responded",
                data={"message": user_message, "response": delegation_plan.get("response", "")[:100]},
                source="J",
            ))
            return delegation_plan.get("response", "How can I help?")
        
        # v3.1: Emit delegation event
        await event_bus.emit(Event(
            type="jarvis.delegated",
            data={
                "message": user_message,
                "intent": delegation_plan.get("intent", ""),
                "tasks": tasks,
            },
            source="J",
        ))
        
        # Delegate to appropriate King(s)
        self.set_state(AgentState.WORKING)

        if len(tasks) > 1:
            results = await self._execute_as_mission(tasks, user_message)
        else:
            results = await self._execute_sequential(tasks, user_message)
        
        self.set_state(AgentState.IDLE)
        
        # Combine results into natural response
        if results:
            combined = "\n\n".join(results)
            try:
                response = await self._compose_response(user_message, combined)
            except Exception:
                response = combined

            # v3.1: Speculative planning — predict follow-ups
            try:
                from ..brain.speculative import speculative_planner
                for task in delegation_plan.get("tasks", []):
                    speculative_planner.predict(task.get("name", "unknown"))
            except Exception:
                pass

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
    
    _KING_ALIASES = {
        "spadek": "♠K", "spadesk": "♠K", "spade_k": "♠K", "spades_k": "♠K",
        "heartk": "♥K", "heartsk": "♥K", "heart_k": "♥K", "hearts_k": "♥K",
        "diamondk": "♦K", "diamondsk": "♦K", "diamond_k": "♦K", "diamonds_k": "♦K",
        "clubk": "♣K", "clubsk": "♣K", "club_k": "♣K", "clubs_k": "♣K",
        "engineering": "♠K", "personal": "♥K", "research": "♦K", "system": "♣K",
    }

    @staticmethod
    def _normalize_king(card_id: str) -> str:
        """Normalize a king card_id — LLM may write 'clubK' instead of '♣K'."""
        clean = card_id.strip().lower().replace(" ", "")
        if clean in JarvisAgent._KING_ALIASES:
            return JarvisAgent._KING_ALIASES[clean]
        # Already a unicode suit? pass through
        if clean and clean[0] in "♠♥♦♣":
            return card_id.strip()
        return card_id.strip()

    async def _analyze_intent(self, message: str) -> dict:
        """Use LLM to analyze user intent and create delegation plan."""
        
        # Build project context for the LLM
        project_context = ""
        try:
            from ..brain.project_memory import project_memory
            active = await project_memory.get_active_project()
            if active:
                project_context = f"""
ACTIVE PROJECT (most recently worked on):
- Name: {active['name']}
- Path: {active['path']}
- Description: {active.get('description', 'N/A')}
- Server: {active.get('server_command', 'N/A')} (port {active.get('server_port', 'N/A')})
- URL: {active.get('url', 'N/A')}
- AI Tool: {active.get('ai_tool_command', 'N/A')}
- Last worked on: {active.get('last_worked_on', 'N/A')}

When the user says things like "proceed with my project", "continue working", "resume", "I'm home let's work", 
and doesn't specify WHICH project, assume they mean the ACTIVE PROJECT listed above.
To resume a project, delegate to ♣K with action "resume_project".
To register a new project, delegate to ♣K with action "register_project".
"""
        except Exception:
            pass

        system_prompt = f"""You are JARVIS, an AI operating system. Analyze the user's request and decide: delegate or talk.

DECISION RULE — memorize this:
  If the request contains ANY of these words → direct_response = false, delegate to a King:
    scan, check, list, find, search, run, open, install, download, upload, create, delete,
    move, copy, rename, read, write, edit, send, schedule, set, fix, update, build, deploy,
    test, analyze, monitor, control, turn on, turn off, connect, configure, manage, explore,
    diagnose, clean, optimize, backup, restore, clone, pull, push, fetch, execute, launch

  If the request is ONLY a greeting, small talk, or question about JARVIS itself → direct_response = true

  WHEN IN DOUBT → direct_response = false. Delegation is always preferred over fabrication.

YOU CANNOT DO ANYTHING YOURSELF. You have NO hands. You can ONLY delegate.
NEVER set a "response" field with fabricated content when direct_response is false.
NEVER claim to have done work. You have done NOTHING until a King reports back.

Available Kings (use EXACTLY these card_ids):
- ♠K (Engineering King): Software development, coding, architecture, testing
- ♥K (Personal King): Calendar, email, tasks, scheduling, personal organization
- ♦K (Research King): Web research, documentation, fact-checking, analysis
- ♣K (System King): File management, terminal commands, system administration, opening apps, resuming projects, scanning system

The "king" field MUST use the exact card_id: ♠K, ♥K, ♦K, or ♣K. Do NOT write "spadeK" or "engineering".

{project_context}

RESPOND WITH ONLY VALID JSON:
{{
    "intent": "<brief description>",
    "tasks": [{{"king": "<king_card_id>", "name": "<task name>", "description": "<what to do>", "priority": 5}}],
    "direct_response": false,
    "response": ""
}}

EXAMPLES (study these carefully):
- "hello" → {{"direct_response": true, "response": "Hello! How can I help?", "tasks": []}}
- "scan my system" → {{"direct_response": false, "tasks": [{{"king": "♣K", "name": "System scan", "description": "Scan the user's computer: list drives, OS info, disk usage, running processes, network info"}}], "response": ""}}
- "what files are on my desktop" → {{"direct_response": false, "tasks": [{{"king": "♣K", "name": "List desktop", "description": "List all files and folders on the Desktop"}}], "response": ""}}
- "search the web for python tutorials" → {{"direct_response": false, "tasks": [{{"king": "♦K", "name": "Web search", "description": "Search for Python tutorials"}}], "response": ""}}
- "I'm home, let's proceed with my project" → {{"direct_response": false, "tasks": [{{"king": "♣K", "name": "Resume project", "description": "Resume the active project"}}], "response": ""}}
- "what is JARVIS?" → {{"direct_response": true, "response": "JARVIS is your AI operating system...", "tasks": []}}"""
        
        response = self._llm.chat_json(
            message=f"User request: {message}",
            system_prompt=system_prompt,
        )
        
        # Normalize king card_ids (LLM may write 'clubK' instead of '♣K')
        for task in response.get("tasks", []):
            if "king" in task:
                task["king"] = self._normalize_king(task["king"])
        
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
    
    async def _execute_as_mission(self, tasks: list, user_message: str) -> list[str]:
        """Execute multiple tasks via the MissionExecutor as a DAG mission."""
        from ..brain.mission_executor import mission_executor

        mission_tasks = []
        for i, task in enumerate(tasks):
            mission_tasks.append({
                "id": f"task_{i}",
                "name": task.get("name", "Task"),
                "description": task.get("description", user_message),
                "assigned_to": task.get("king", "♠K"),
                "priority": task.get("priority", 5),
            })

        create_result = mission_executor.create_and_execute(user_message, mission_tasks)
        if not create_result.get("ok"):
            return [f"Failed to create mission: {create_result.get('error', 'unknown')}"]

        mission_id = create_result["mission_id"]
        final_status = await mission_executor.execute_mission(mission_id)

        results = []
        nodes = dag_planner._missions.get(mission_id, [])
        for node in nodes:
            results.append(f"[{node.name}] {node.result or node.status.value}")

        return results if results else [f"Mission finished: {final_status.get('progress', 0):.0%} complete"]

    async def _execute_sequential(self, tasks: list, user_message: str) -> list[str]:
        """Execute single tasks sequentially (original behavior)."""
        results = []
        for task in tasks:
            king_card = task.get("king", "♠K")
            king = self._kings.get(king_card)

            if king is None:
                results.append(f"No King found for {king_card}")
                continue

            task_obj = Task(
                name=task.get("name", "User request"),
                description=task.get("description", user_message),
                assigned_to=king_card,
                priority=task.get("priority", 5),
            )

            try:
                result = await king.execute_task(task_obj)
                results.append(result.content)
            except Exception as e:
                results.append(f"Error from {king.name}: {e}")

        return results

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
