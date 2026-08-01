"""
JARVIS Native Architecture - Wraps the existing JARVIS agent system.
"""

from datetime import datetime
from typing import Any

from ...brain.llm import LLM
from ..base import (
    AgentArchitecture,
    ArchitectureState,
    ExecutionResult,
    MissionContext,
    Plan,
    PlanStep,
)


class JarvisNativeArchitecture(AgentArchitecture):
    """
    JARVIS Native Architecture - wraps the existing Kings/Workers system.
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._jarvis = None
        self._llm = LLM()
        self._tools = None

    @property
    def name(self) -> str:
        return "JARVIS Native"

    @property
    def version(self) -> str:
        return "8.0.0"

    @property
    def description(self) -> str:
        return (
            "Native JARVIS multi-agent architecture with Kings "
            "(Engineering, Personal, Research, System) and specialized Workers."
        )

    @property
    def capabilities(self) -> list[str]:
        return [
            "multi_agent_orchestration",
            "king_worker_delegation",
            "tool_execution",
            "computer_control",
            "browser_automation",
            "web_research",
            "code_execution",
            "file_management",
            "voice_io",
            "iot_control",
            "mission_pipeline",
            "memory_management",
            "context_preservation",
        ]

    async def initialize(self) -> bool:
        """Initialize the native architecture by connecting to existing JARVIS."""
        try:
            # Import existing JARVIS components
            from ...computer.controller import controller as tool_controller
            from ...web.main import jarvis as jarvis_instance

            self._jarvis = jarvis_instance
            self._tools = tool_controller
            self._initialized = True
            self.state = ArchitectureState.IDLE
            return True
        except Exception as e:
            print(f"Failed to initialize JARVIS Native Architecture: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the architecture."""
        self._jarvis = None
        self._tools = None
        self._initialized = False
        self.state = ArchitectureState.IDLE

    async def plan(self, mission: MissionContext) -> Plan:
        """Create a plan using the existing JARVIS delegation system."""
        self.state = ArchitectureState.PLANNING

        # Get available tools
        tool_list = self._get_tool_list()

        # Use LLM to create a structured plan
        system_prompt = self._build_planning_prompt(mission, tool_list)

        response = self._llm.chat(
            message=f"Mission: {mission.user_request}\nGoal: {mission.mission_id}",
            system_prompt=system_prompt,
            temperature=0.3,
        )

        # Parse response into Plan
        plan = self._parse_plan_response(response, mission)

        self.state = ArchitectureState.IDLE
        return plan

    async def execute(self, mission: MissionContext, plan: Plan) -> list[ExecutionResult]:
        """Execute the plan using the existing agent hierarchy."""
        self.state = ArchitectureState.EXECUTING
        results = []

        for step in plan.steps:
            mission.current_step = step
            step.status = "running"
            step.started_at = datetime.now()

            self.state = ArchitectureState.EXECUTING

            try:
                # Execute the step using available tools
                if step.tool:
                    result = await self._execute_tool(step.tool, step.params)
                else:
                    # Delegate to JARVIS agent hierarchy
                    result = await self._delegate_to_jarvis(step, mission)

                step.result = result
                step.status = "completed"
                step.completed_at = datetime.now()

                exec_result = ExecutionResult(
                    step_id=step.id,
                    success=True,
                    output=result,
                    duration_ms=(step.completed_at - step.started_at).total_seconds() * 1000,
                )

            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                step.completed_at = datetime.now()

                exec_result = ExecutionResult(
                    step_id=step.id,
                    success=False,
                    error=str(e),
                    duration_ms=(step.completed_at - step.started_at).total_seconds() * 1000,
                )

            # Verify the result
            self.state = ArchitectureState.VERIFYING
            verification = await self.verify(step, exec_result)
            exec_result.verification = verification

            # Observe the result
            self.state = ArchitectureState.OBSERVING
            observations = await self.observe(mission, exec_result)

            # Store in mission context
            mission.executed_steps.append(exec_result)
            mission.working_memory[f"step_{step.id}_observations"] = observations

            results.append(exec_result)

            # Check if we should continue
            if not exec_result.success and not self._should_continue_on_failure(step, plan):
                break

        self.state = ArchitectureState.IDLE
        return results

    async def observe(
        self, mission: MissionContext, step_result: ExecutionResult
    ) -> dict[str, Any]:
        """Observe and analyze the result of a step execution."""
        observations = {
            "timestamp": datetime.now().isoformat(),
            "step_id": step_result.step_id,
            "success": step_result.success,
            "output_summary": str(step_result.output)[:200] if step_result.output else None,
            "error": step_result.error,
        }

        # Use LLM to analyze the result
        if mission.current_step:
            analysis_prompt = f"""
            Analyze the result of this step:
            Step: {mission.current_step.name}
            Description: {mission.current_step.description}
            Tool used: {mission.current_step.tool}
            Success: {step_result.success}
            Output: {str(step_result.output)[:500]}
            Error: {step_result.error}

            Provide brief observations on:
            1. What was accomplished
            2. Any issues or anomalies
            3. Suggestions for next steps
            """

            analysis = self._llm.chat(analysis_prompt, temperature=0.3)
            observations["analysis"] = analysis

        return observations

    async def reflect(self, mission: MissionContext) -> dict[str, Any]:
        """Reflect on the completed mission."""
        reflection = {
            "mission_id": mission.mission_id,
            "goal": mission.user_request,
            "total_steps": len(mission.plan.steps) if mission.plan else 0,
            "completed_steps": sum(1 for r in mission.executed_steps if r.success),
            "failed_steps": sum(1 for r in mission.executed_steps if not r.success),
            "total_duration_ms": sum(r.duration_ms for r in mission.executed_steps),
            "timestamp": datetime.now().isoformat(),
        }

        # Use LLM for deeper reflection
        if mission.executed_steps:
            reflection_prompt = f"""
            Reflect on this completed mission:
            Goal: {mission.user_request}
            Steps executed: {len(mission.executed_steps)}
            Successes: {reflection["completed_steps"]}
            Failures: {reflection["failed_steps"]}

            Step results:
            {self._format_steps_for_reflection(mission.executed_steps)}

            Provide reflection on:
            1. What went well
            2. What could be improved
            3. Patterns noticed
            4. Lessons for future missions
            """

            reflection["llm_reflection"] = self._llm.chat(reflection_prompt, temperature=0.4)

        return reflection

    async def verify(self, step: PlanStep, result: ExecutionResult) -> dict[str, Any]:
        """Verify the result of a step execution."""
        verification = {
            "step_id": step.id,
            "verified": result.success,
            "confidence": 1.0 if result.success else 0.0,
            "checks": [],
        }

        if not result.success:
            verification["confidence"] = 0.0
            verification["checks"].append(
                {"check": "step_success", "passed": False, "message": result.error or "Step failed"}
            )
            return verification

        # Basic verification checks
        if step.expected_outcome and result.output:
            # Use LLM to verify output matches expectation
            verify_prompt = f"""
            Check if the output matches the expected outcome.
            Expected: {step.expected_outcome}
            Actual: {str(result.output)[:1000]}
            Tool used: {step.tool}

            Respond with JSON:
            {{
                "matches": true/false,
                "confidence": 0.0-1.0,
                "details": "explanation"
            }}
            """

            try:
                verify_response = self._llm.chat(verify_prompt, temperature=0.1)
                # Parse verification result
                import json as _json

                verify_data = _json.loads(verify_response)
                verification["checks"].append(
                    {
                        "check": "outcome_match",
                        "passed": verify_data.get("matches", True),
                        "confidence": verify_data.get("confidence", 1.0),
                        "details": verify_data.get("details", ""),
                    }
                )
                verification["confidence"] = verify_data.get("confidence", 1.0)
            except Exception:
                verification["checks"].append(
                    {
                        "check": "outcome_match",
                        "passed": True,
                        "confidence": 0.8,
                        "details": "Could not verify - assuming match",
                    }
                )

        return verification

    async def remember(
        self, mission: MissionContext, key: str, value: Any, memory_type: str = "working"
    ) -> None:
        """Store information in mission memory."""
        if memory_type == "working":
            mission.working_memory[key] = value
        elif memory_type == "short_term":
            # Could store in a short-term memory system
            pass
        elif memory_type == "long_term":
            # Could store in a long-term memory system
            pass
        elif memory_type == "project":
            mission.long_term_memory[key] = value

    async def recall(self, mission: MissionContext, key: str, memory_type: str = "working") -> Any:
        """Retrieve information from mission memory."""
        if memory_type == "working":
            return mission.working_memory.get(key)
        elif memory_type == "project":
            return mission.long_term_memory.get(key)
        return None

    def get_status(self) -> dict[str, Any]:
        """Get current architecture status."""
        return {
            "name": self.name,
            "version": self.version,
            "state": self.state.value,
            "initialized": self._initialized,
            "current_mission": self.current_mission.mission_id if self.current_mission else None,
        }

    def get_config_schema(self) -> dict[str, Any]:
        """Return JSON schema for configuration options."""
        return {
            "type": "object",
            "properties": {
                "llm_temperature": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.7},
                "max_retries": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
                "verification_enabled": {"type": "boolean", "default": True},
                "auto_continue_on_failure": {"type": "boolean", "default": False},
            },
        }

    # --- Private helper methods ---

    def _get_tool_list(self) -> str:
        """Get list of available tools."""
        if self._tools:
            return ", ".join(self._tools.list_actions())
        return ""

    def _build_planning_prompt(self, mission: MissionContext, tool_list: str) -> str:
        """Build system prompt for planning."""
        return f"""You are the planning engine for JARVIS Native Architecture.

Mission: {mission.user_request}

Available tools: {tool_list}

Create a detailed plan with these steps:
1. Break down the mission into logical steps
2. Assign appropriate tools to each step
3. Define expected outcomes
4. Identify dependencies between steps
5. Consider potential failure points

Output as JSON:
{{
    "steps": [
        {{
            "name": "step name",
            "description": "what this step does",
            "tool": "tool_name_or_null",
            "params": {{"param": "value"}},
            "expected_outcome": "what success looks like",
            "dependencies": ["step_id"]
        }}
    ]
}}"""

    def _parse_plan_response(self, response: str, mission: MissionContext) -> Plan:
        """Parse LLM response into Plan object."""
        import json as _json
        import re

        # Try to extract JSON from response
        try:
            # Find JSON block
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = _json.loads(json_match.group())
            else:
                data = _json.loads(response)
        except Exception:
            # Fallback: create simple plan
            return Plan(
                goal=mission.user_request,
                steps=[
                    PlanStep(
                        name="Execute Mission",
                        description=mission.user_request,
                        tool=None,
                        expected_outcome="Mission completed",
                    )
                ],
            )

        steps = []
        for i, step_data in enumerate(data.get("steps", [])):
            step = PlanStep(
                id=f"step_{i + 1}",
                name=step_data.get("name", f"Step {i + 1}"),
                description=step_data.get("description", ""),
                tool=step_data.get("tool"),
                params=step_data.get("params", {}),
                expected_outcome=step_data.get("expected_outcome", ""),
                dependencies=step_data.get("dependencies", []),
            )
            steps.append(step)

        return Plan(goal=mission.user_request, steps=steps)

    async def _execute_tool(self, tool_name: str, params: dict[str, Any]) -> Any:
        """Execute a tool using the tool controller."""
        if self._tools:
            return await self._tools.execute(tool_name, **params)
        raise Exception(f"Tool controller not available: {tool_name}")

    async def _delegate_to_jarvis(self, step: PlanStep, mission: MissionContext) -> Any:
        """Delegate to the existing JARVIS agent hierarchy."""
        if self._jarvis:
            return await self._jarvis.process_user_request(step.description)
        raise Exception("JARVIS instance not available")

    def _should_continue_on_failure(self, step: PlanStep, plan: Plan) -> bool:
        """Determine if execution should continue after a step failure."""
        # Check if any dependent steps exist
        for s in plan.steps:
            if step.id in s.dependencies:
                return False  # Don't continue if other steps depend on this one
        return True

    def _format_steps_for_reflection(self, steps: list[ExecutionResult]) -> str:
        """Format step results for LLM reflection."""
        lines = []
        for r in steps:
            status = "✓" if r.success else "✗"
            lines.append(f"  {status} Step {r.step_id}: {r.output[:100] if r.output else r.error}")
        return "\n".join(lines)
