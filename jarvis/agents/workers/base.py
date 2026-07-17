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
    Override get_model_config() to use a different LLM per worker.
    """
    
    def __init__(self, suit: Suit, rank: Rank):
        super().__init__(suit=suit, rank=rank)
        config = self.get_model_config()
        self._llm = LLM(
            model=config.get("model"),
            api_base=config.get("api_base"),
            api_key=config.get("api_key"),
        )
        self._tools = None  # Lazy-loaded ToolExecutor
    
    def get_model_config(self) -> dict:
        """Override to use a different LLM for this worker.
        
        Returns dict with optional keys: model, api_base, api_key
        Example: {"model": "meta/llama-3.1-8b-instruct", "api_base": "https://..."}
        """
        return {}
    
    def get_tools(self):
        """Get the tool executor for computer control."""
        if self._tools is None:
            from ...computer.controller import controller
            self._tools = controller
        return self._tools
    
    @property
    def role(self):
        from ...core.models import AgentRole
        return AgentRole.WORKER
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this worker's specialization."""
        pass
    
    async def execute_task(self, task: Task) -> AgentMessage:
        """Execute a task and return result with confidence.
        
        Workers can now use tools (computer control, web search, IoT)
        by having the LLM call them via tool_use format in the response.
        """
        self.set_state(AgentState.WORKING)

        # v3.1: Emit event
        from ...core.events import event_bus, Event
        await event_bus.emit(Event(
            type="worker.started",
            data={"worker": self.card_id, "task": task.name},
            source=self.card_id,
        ))
        
        try:
            # Get specialized system prompt
            system_prompt = self.get_system_prompt()
            
            # Add tool instructions
            tool_list = ", ".join(self.get_tools().list_actions())
            tool_prompt = f"""

You have access to tools. To use a tool, include in your response:
[TOOL: action_name(param1="value1", param2="value2")]

Available tools: {tool_list}

Examples:
- [TOOL: web_search(query="python async tutorial")]
- [TOOL: screen_capture()]
- [TOOL: browser_navigate(url="https://example.com")]
- [TOOL: arduino_send(device_id="esp32_01", command="ledon")]
- [TOOL: shell_execute(command="ls -la")]

After receiving tool results, continue your work. When done, provide your final answer.
"""
            
            full_prompt = system_prompt + tool_prompt
            
            # Execute via LLM with tool loop (max 5 tool calls)
            response = self._llm.chat(
                message=f"Task: {task.name}\n\nDescription: {task.description}",
                system_prompt=full_prompt,
            )
            
            # Process tool calls in the response
            response = await self._process_tool_calls(response)
            
            # Assess confidence
            confidence = await self._assess_confidence(task, response)
            
            # Identify issues
            issues = await self._identify_issues(task, response)
            
            self.set_state(AgentState.COMPLETED)

            # v3.1: Emit completion event
            await event_bus.emit(Event(
                type="worker.completed",
                data={
                    "worker": self.card_id,
                    "task": task.name,
                    "confidence": confidence,
                    "issues": issues,
                },
                source=self.card_id,
            ))
            
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

            # v3.1: Emit error event
            await event_bus.emit(Event(
                type="worker.error",
                data={
                    "worker": self.card_id,
                    "task": task.name,
                    "error": str(e),
                },
                source=self.card_id,
            ))
            
            return AgentMessage(
                sender=self.card_id,
                receiver="K",
                task_id=task.id,
                content=f"Error executing task: {str(e)}",
                status="error",
                confidence=0.0,
                issues=[str(e)],
            )
    
    async def _process_tool_calls(self, response: str) -> str:
        """Parse and execute tool calls from LLM response."""
        import re
        
        tool_executor = self.get_tools()
        max_iterations = 5
        
        for _ in range(max_iterations):
            # Find tool calls: [TOOL: action(param="val", ...)]
            pattern = r'\[TOOL:\s*(\w+)\((.*?)\)\]'
            matches = re.findall(pattern, response)
            
            if not matches:
                break
            
            for action_str, args_str in matches:
                # Parse arguments
                params = {}
                if args_str.strip():
                    # Simple key="value" parsing
                    for arg in re.findall(r'(\w+)="([^"]*)"', args_str):
                        params[arg[0]] = arg[1]
                    # Also handle key=value without quotes
                    for arg in re.findall(r'(\w+)=(\d+\.?\d*)', args_str):
                        if arg[0] not in params:
                            try:
                                params[arg[0]] = float(arg[1])
                                if params[arg[0]] == int(params[arg[0]]):
                                    params[arg[0]] = int(params[arg[0]])
                            except ValueError:
                                params[arg[0]] = arg[1]
                
                # Execute the tool
                result = await tool_executor.execute(action_str, **params)
                
                # Format result for the LLM
                result_str = f"\n[TOOL RESULT: {action_str}] {result}\n"
                
                # Append result and get new response
                response = self._llm.chat(
                    message=f"Tool result for {action_str}:\n{result_str}\n\nContinue your work.",
                    system_prompt="Process the tool result and continue.",
                )
        
        return response
    
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
