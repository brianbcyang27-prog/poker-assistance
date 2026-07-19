"""Base Worker — Specialized task executor with cross-agent collaboration (v6.1.0)."""

import asyncio
import json
import re
from abc import abstractmethod
from typing import Optional

from ..base import CardAgent
from ...core.models import Suit, Rank, AgentState, AgentMessage, Task
from ...brain.llm import LLM


class BaseWorker(CardAgent):
    """Base class for Worker agents with collaboration capabilities.

    Workers perform focused jobs. Workers NEVER talk to the user.
    Workers report to Kings. Workers CAN collaborate with each other
    via the event bus.
    """

    def __init__(self, suit: Suit, rank: Rank):
        super().__init__(suit=suit, rank=rank)
        config = self.get_model_config()
        self._llm = LLM(
            model=config.get("model"),
            api_base=config.get("api_base"),
            api_key=config.get("api_key"),
        )
        self._tools = None
        self._pending_help: dict[str, asyncio.Future] = {}
        self._peer_results: dict[str, str] = {}

    def get_model_config(self) -> dict:
        return {}

    def get_tools(self):
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
        pass

    # === Collaboration Methods ===

    async def request_help(self, question: str, task_id: str = "") -> Optional[str]:
        """Request help from a peer worker via the event bus.

        Emits a worker.help_request event and waits up to 15s for a response.
        """
        from ...core.events import event_bus, Event

        request_id = f"help_{self.card_id}_{task_id}_{id(question)}"
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_help[request_id] = future

        await event_bus.emit(Event(
            type="worker.help_request",
            data={
                "worker": self.card_id,
                "request_id": request_id,
                "question": question,
                "task_id": task_id,
            },
            source=self.card_id,
        ))

        try:
            response = await asyncio.wait_for(future, timeout=15.0)
            return response
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending_help.pop(request_id, None)

    async def respond_to_help(self, request_id: str, responder: str, answer: str):
        """Respond to a help request from a peer."""
        from ...core.events import event_bus, Event

        await event_bus.emit(Event(
            type="worker.help_response",
            data={
                "responder": responder,
                "request_id": request_id,
                "answer": answer,
            },
            source=self.card_id,
        ))

    async def share_result(self, task_name: str, result_summary: str):
        """Share a result with peers via the event bus."""
        from ...core.events import event_bus, Event

        await event_bus.emit(Event(
            type="worker.result_shared",
            data={
                "worker": self.card_id,
                "task": task_name,
                "summary": result_summary[:500],
            },
            source=self.card_id,
        ))

    async def broadcast(self, message_type: str, data: dict):
        """Broadcast a discovery or status to all peers."""
        from ...core.events import event_bus, Event

        await event_bus.emit(Event(
            type=f"worker.broadcast.{message_type}",
            data={"worker": self.card_id, **data},
            source=self.card_id,
        ))

    def _setup_collaboration_listener(self):
        """Subscribe to events from peers. Called once during initialization."""
        from ...core.events import event_bus

        async def _on_help_response(event):
            req_id = event.data.get("request_id", "")
            if req_id in self._pending_help and not self._pending_help[req_id].done():
                self._pending_help[req_id].set_result(event.data.get("answer", ""))

        async def _on_result_shared(event):
            worker_id = event.data.get("worker", "")
            if worker_id != self.card_id:
                self._peer_results[worker_id] = event.data.get("summary", "")

        event_bus.on("worker.help_response", _on_help_response)
        event_bus.on("worker.result_shared", _on_result_shared)
    
    async def execute_task(self, task: Task, peer_context: str = "") -> AgentMessage:
        """Execute a task and return result with confidence.

        Args:
            task: The task to execute.
            peer_context: Results from previously completed workers in the same mission.
        """
        from ...core.events import event_bus, Event

        self.set_state(AgentState.WORKING)
        self._setup_collaboration_listener()

        await event_bus.emit(Event(
            type="worker.started",
            data={"worker": self.card_id, "task": task.name},
            source=self.card_id,
        ))

        try:
            system_prompt = self.get_system_prompt()

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

You can also request help from peer workers:
[HELP_REQUEST: Describe what you need help with]

After receiving tool results or peer help, continue your work. When done, provide your final answer.
"""
            full_prompt = system_prompt + tool_prompt

            # Build message with peer context if available
            message = f"Task: {task.name}\n\nDescription: {task.description}"
            if peer_context:
                message += f"\n\n=== Results from other workers ===\n{peer_context}"
            if self._peer_results:
                summaries = "\n".join(
                    f"- {wid}: {res[:200]}" for wid, res in self._peer_results.items()
                )
                message += f"\n\n=== Available peer discoveries ===\n{summaries}"

            response = self._llm.chat(message=message, system_prompt=full_prompt)
            response = await self._process_tool_calls(response)

            confidence = await self._assess_confidence(task, response)
            issues = await self._identify_issues(task, response)

            # Review pipeline
            try:
                from ...brain.review import review_pipeline
                review = await review_pipeline.review(
                    task_type=task.name,
                    task_description=task.description,
                    result=response,
                    confidence=confidence,
                    issues=issues,
                )
                if review.verdict.value == "fail":
                    status = "completed_with_issues"
                else:
                    status = "completed"
                issues = list(set(issues + review.issues))
            except Exception:
                review = None
                status = "completed"

            self.set_state(AgentState.COMPLETED)

            # Share result with peers
            await self.share_result(task.name, response[:500])

            await event_bus.emit(Event(
                type="worker.completed",
                data={
                    "worker": self.card_id,
                    "task": task.name,
                    "confidence": confidence,
                    "issues": issues,
                    "review": review.to_dict() if review else None,
                },
                source=self.card_id,
            ))

            return AgentMessage(
                sender=self.card_id,
                receiver="K",
                task_id=task.id,
                content=response,
                status="completed",
                confidence=confidence,
                issues=issues,
            )

        except Exception as e:
            self.set_state(AgentState.ERROR)
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
        tool_executor = self.get_tools()
        max_iterations = 5

        for _ in range(max_iterations):
            # Handle help requests
            help_matches = re.findall(r'\[HELP_REQUEST:\s*(.*?)\]', response)
            for question in help_matches:
                answer = await self.request_help(question)
                if answer:
                    response += f"\n\n[PEER HELP]: {answer}"
                else:
                    response += "\n\n[PEER HELP]: No peer available to help."

            # Find tool calls: [TOOL: action(param="val", ...)]
            pattern = r'\[TOOL:\s*(\w+)\((.*?)\)\]'
            matches = re.findall(pattern, response)

            if not matches:
                break

            for action_str, args_str in matches:
                params = {}
                if args_str.strip():
                    for arg in re.findall(r'(\w+)="([^"]*)"', args_str):
                        params[arg[0]] = arg[1]
                    for arg in re.findall(r'(\w+)=(\d+\.?\d*)', args_str):
                        if arg[0] not in params:
                            try:
                                params[arg[0]] = float(arg[1])
                                if params[arg[0]] == int(params[arg[0]]):
                                    params[arg[0]] = int(params[arg[0]])
                            except ValueError:
                                params[arg[0]] = arg[1]

                await event_bus.emit(Event(
                    type="worker.tool_call",
                    data={
                        "worker": self.card_id,
                        "action": action_str,
                        "params": str(params)[:100],
                    },
                    source=self.card_id,
                ))

                result = await tool_executor.execute(action_str, **params)
                result_str = f"\n[TOOL RESULT: {action_str}] {result}\n"
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
        """Process messages from peers (help requests, shared results)."""
        if message.status == "help_request":
            answer = self._handle_help_request(message.content)
            return AgentMessage(
                sender=self.card_id,
                receiver=message.sender,
                task_id=message.task_id,
                content=answer,
                status="help_response",
            )
        return None

    def _handle_help_request(self, question: str) -> str:
        """Answer a help request based on this worker's knowledge."""
        try:
            response = self._llm.chat(
                message=f"A peer worker asked: {question}\n\nProvide a brief, helpful answer based on your expertise.",
                system_prompt=f"You are {self.name}, a {self.title}. Help a peer with their question briefly.",
                temperature=0.3,
            )
            return response
        except Exception:
            return "I'm unable to help with that right now."
