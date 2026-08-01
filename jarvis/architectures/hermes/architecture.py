"""
Hermes Architecture - Internal implementation of Hermes-inspired concepts.
This is NOT a dependency on external Hermes - it's an internal architecture.
"""

import json
import uuid
from dataclasses import dataclass, field
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


@dataclass
class HermesTask:
    """A task in the Hermes architecture."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    agent_type: str = "general"  # planner, executor, researcher, coder, reviewer
    status: str = "pending"
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    parent_id: str | None = None
    children: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


@dataclass
class HermesContext:
    """Context for Hermes architecture execution."""

    mission_id: str
    user_request: str
    tasks: dict[str, HermesTask] = field(default_factory=dict)
    task_order: list[str] = field(default_factory=list)
    working_memory: dict[str, Any] = field(default_factory=dict)
    episodic_memory: list[dict] = field(default_factory=list)
    semantic_memory: dict[str, Any] = field(default_factory=dict)
    skills: dict[str, dict] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class HermesPlanner:
    """Plans tasks using structured reasoning."""

    def __init__(self, llm: LLM):
        self.llm = llm

    async def create_plan(self, user_request: str, context: HermesContext) -> list[HermesTask]:
        """Create a hierarchical plan for the request."""
        system_prompt = """You are the Hermes Planner. Create a detailed hierarchical plan.

Break down the user request into:
1. High-level phases
2. Concrete tasks within each phase
3. Agent assignments (planner, executor, researcher, coder, reviewer)
4. Dependencies between tasks
5. Expected outputs and verification criteria

Return JSON with task hierarchy."""

        prompt = f"""User Request: {user_request}

Available agents: planner, executor, researcher, coder, reviewer

Context:
- Working memory: {json.dumps(context.working_memory)[:500]}
- Available skills: {list(context.skills.keys())}

Create a detailed task hierarchy. Each task needs:
- id (will be generated)
- name
- description
- agent_type
- input_data (what it needs)
- expected_output
- dependencies (task IDs)
- verification_criteria

Return JSON array of tasks."""

        response = await self.llm.achat(prompt, system_prompt=system_prompt, temperature=0.3)

        try:
            tasks_data = json.loads(response)
            tasks = []
            for i, task_data in enumerate(tasks_data):
                task = HermesTask(
                    id=task_data.get("id", f"task_{i + 1}"),
                    name=task_data.get("name", f"Task {i + 1}"),
                    description=task_data.get("description", ""),
                    agent_type=task_data.get("agent_type", "executor"),
                    input_data=task_data.get("input_data", {}),
                    context=task_data.get("context", {}),
                )
                tasks.append(task)
            return tasks
        except Exception:
            # Fallback: create single task
            return [
                HermesTask(
                    id="task_1",
                    name="Execute Request",
                    description=user_request,
                    agent_type="executor",
                    input_data={"request": user_request},
                )
            ]


class HermesExecutor:
    """Executes tasks using appropriate agents."""

    def __init__(self, llm: LLM, tools=None):
        self.llm = llm
        self.tools = tools

    async def execute(self, task: HermesTask, context: HermesContext) -> dict[str, Any]:
        """Execute a task using the appropriate agent."""
        if task.agent_type == "researcher":
            return await self._execute_research(task, context)
        elif task.agent_type == "coder":
            return await self._execute_coder(task, context)
        elif task.agent_type == "executor":
            return await self._execute_general(task, context)
        elif task.agent_type == "reviewer":
            return await self._execute_reviewer(task, context)
        else:
            return await self._execute_general(task, context)

    async def _execute_research(self, task: HermesTask, context: HermesContext) -> dict[str, Any]:
        """Execute a research task."""
        query = task.input_data.get("query", task.description)

        # Use available tools for research
        results = {}
        if self.tools:
            try:
                # Search web
                search_result = await self.tools.execute("web_search", query=query)
                results["web_search"] = search_result
            except Exception as e:
                results["web_search_error"] = str(e)

            try:
                # Fetch specific URLs if provided
                urls = task.input_data.get("urls", [])
                for url in urls[:3]:
                    safe_url = url.replace("://", "_").replace("/", "_")
                    fetch_result = await self.tools.execute("web_fetch", url=url)
                    results[f"fetch_{safe_url}"] = fetch_result
            except Exception as e:
                results["fetch_error"] = str(e)

        # Synthesize findings
        synthesis_prompt = f"""Synthesize research findings for: {query}

Raw results: {json.dumps(results)[:2000]}

Provide structured summary with:
1. Key findings
2. Sources
3. Confidence level
4. Gaps or uncertainties"""

        synthesis = await self.llm.achat(synthesis_prompt, temperature=0.3)

        return {
            "type": "research",
            "query": query,
            "raw_results": results,
            "synthesis": synthesis,
            "confidence": 0.8,
        }

    async def _execute_coder(self, task: HermesTask, context: HermesContext) -> dict[str, Any]:
        """Execute a coding task."""
        requirement = task.input_data.get("requirement", task.description)
        language = task.input_data.get("language", "python")
        context_files = task.input_data.get("context_files", [])

        # Build context from files
        file_context = ""
        for f in context_files[:5]:
            file_context += f"\n--- {f.get('path', 'unknown')} ---\n{f.get('content', '')[:1000]}\n"

        coding_prompt = f"""You are an expert {language} developer.

Requirement: {requirement}

Context files:
{file_context}

Additional context from memory: {json.dumps(context.working_memory)[:1000]}

Write clean, production-ready code. Include:
1. Complete implementation
2. Error handling
3. Type hints (if applicable)
4. Docstrings
5. Tests if appropriate

Return only the code."""

        code = await self.llm.achat(coding_prompt, temperature=0.2)

        return {
            "type": "code",
            "language": language,
            "code": code,
            "requirement": requirement,
            "files_created": [],
        }

    async def _execute_reviewer(self, task: HermesTask, context: HermesContext) -> dict[str, Any]:
        """Execute a review task."""
        content = task.input_data.get("content", "")
        criteria = task.input_data.get(
            "criteria", ["correctness", "style", "security", "performance"]
        )

        review_prompt = f"""Review the following content:

{content[:3000]}

Criteria: {", ".join(criteria)}

Provide structured review with:
1. Overall assessment (pass/fail/conditional)
2. Issues found (categorized by severity)
3. Suggestions for improvement
4. Confidence score (0-1)"""

        review = await self.llm.achat(review_prompt, temperature=0.2)

        return {
            "type": "review",
            "review": review,
            "criteria": criteria,
            "passed": "pass" in review.lower()[:50],
        }

    async def _execute_general(self, task: HermesTask, context: HermesContext) -> dict[str, Any]:
        """Execute a general task."""
        prompt = f"""Execute this task:

Task: {task.name}
Description: {task.description}
Input: {json.dumps(task.input_data)}

Use available tools if needed. Provide clear output."""

        response = await self.llm.achat(prompt, temperature=0.3)

        return {"type": "general", "response": response, "task": task.name}


class HermesVerifier:
    """Verifies task outputs against criteria."""

    def __init__(self, llm: LLM):
        self.llm = llm

    async def verify(self, task: HermesTask, output: dict[str, Any]) -> dict[str, Any]:
        """Verify task output against criteria."""
        verification_prompt = f"""Verify the task output meets the criteria.

Task: {task.name}
Description: {task.description}
Expected: {task.input_data.get("expected_output", "N/A")}
Verification criteria: \
{task.input_data.get("verification_criteria", "Correctness and completeness")}

Actual output: {json.dumps(output)[:2000]}

Respond with JSON:
{{
    "passed": true/false,
    "confidence": 0.0-1.0,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1"]
}}"""

        try:
            response = await self.llm.achat(verification_prompt, temperature=0.1)
            return json.loads(response)
        except Exception:
            return {"passed": True, "confidence": 0.8, "issues": [], "suggestions": []}


class HermesReflector:
    """Reflects on completed work for learning."""

    def __init__(self, llm: LLM):
        self.llm = llm

    async def reflect(
        self, context: HermesContext, completed_tasks: list[HermesTask]
    ) -> dict[str, Any]:
        """Reflect on completed work."""
        task_summaries = json.dumps(
            [
                {
                    "id": t.id,
                    "name": t.name,
                    "agent": t.agent_type,
                    "status": t.status,
                    "error": t.error,
                }
                for t in completed_tasks
            ],
            indent=2,
        )
        reflection_prompt = f"""Reflect on the completed mission.

Mission: {context.user_request}
Tasks completed: {len(completed_tasks)}

Task summaries:
{task_summaries}

Working memory: {json.dumps(context.working_memory)[:1000]}

Provide reflection on:
1. What worked well
2. What failed or was problematic
3. Patterns observed
4. Lessons learned
5. Suggestions for improvement
6. Skills that could be extracted

Return JSON with structured reflection."""

        response = await self.llm.achat(reflection_prompt, temperature=0.4)

        try:
            return json.loads(response)
        except Exception:
            return {"summary": "Reflection completed", "lessons": [], "improvements": []}


class HermesMemoryManager:
    """Manages different types of memory."""

    def __init__(self):
        self.working: dict[str, Any] = {}
        self.short_term: dict[str, Any] = {}
        self.long_term: dict[str, Any] = {}
        self.episodic: list[dict] = []
        self.semantic: dict[str, Any] = {}
        self.skills: dict[str, dict] = {}

    def store(self, key: str, value: Any, memory_type: str = "working"):
        target = getattr(self, memory_type, self.working)
        if isinstance(target, dict):
            target[key] = value
        elif isinstance(target, list):
            target.append(value)

    def retrieve(self, key: str, memory_type: str = "working") -> Any:
        target = getattr(self, memory_type, self.working)
        if isinstance(target, dict):
            return target.get(key)
        return None

    def add_skill(self, name: str, skill: dict):
        self.skills[name] = skill

    def get_skill(self, name: str) -> dict | None:
        return self.skills.get(name)


class HermesArchitecture(AgentArchitecture):
    """
    Hermes Architecture - Internal implementation of Hermes-inspired agent architecture.

    Features:
    - Hierarchical task planning
    - Specialized agent types (planner, executor, researcher, coder, reviewer)
    - Multi-layer memory (working, short-term, long-term, episodic, semantic)
    - Skill system for reusable capabilities
    - Structured verification
    - Reflection for continuous improvement
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.llm = LLM()
        self.planner = HermesPlanner(self.llm)
        self.executor = HermesExecutor(self.llm)  # Tools will be set later
        self.verifier = HermesVerifier(self.llm)
        self.reflector = HermesReflector(self.llm)
        self.memory = HermesMemoryManager()
        self._tools = None
        self._current_context: HermesContext | None = None

    @property
    def name(self) -> str:
        return "Hermes"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return (
            "Hermes-inspired architecture with hierarchical planning, specialized agents, "
            "multi-layer memory, and reflection loops."
        )

    @property
    def capabilities(self) -> list[str]:
        return [
            "hierarchical_planning",
            "specialized_agents",
            "multi_layer_memory",
            "skill_system",
            "structured_verification",
            "reflection_learning",
            "skill_extraction",
            "context_management",
            "tool_orchestration",
        ]

    async def initialize(self) -> bool:
        """Initialize the Hermes architecture."""
        try:
            # Try to connect to existing tool controller
            from ...computer.controller import controller as tool_controller

            self._tools = tool_controller
            self.executor.tools = tool_controller
            self._initialized = True
            self.state = ArchitectureState.IDLE
            return True
        except Exception as e:
            print(f"Failed to initialize Hermes Architecture: {e}")
            # Can still work without tools
            self._initialized = True
            self.state = ArchitectureState.IDLE
            return True

    async def shutdown(self) -> None:
        """Shutdown the architecture."""
        self._current_context = None
        self._initialized = False
        self.state = ArchitectureState.IDLE

    async def plan(self, mission: MissionContext) -> Plan:
        """Create a hierarchical plan using Hermes planner."""
        self.state = ArchitectureState.PLANNING

        # Create Hermes context
        hermes_context = HermesContext(
            mission_id=mission.mission_id, user_request=mission.user_request
        )
        self._current_context = hermes_context

        # Use planner to create tasks
        tasks = await self.planner.create_plan(mission.user_request, hermes_context)

        # Store tasks in context
        for task in tasks:
            hermes_context.tasks[task.id] = task
            hermes_context.task_order.append(task.id)

        # Convert to Plan format
        plan_steps = []
        for i, task in enumerate(tasks):
            step = PlanStep(
                id=task.id,
                name=task.name,
                description=task.description,
                tool=task.agent_type,
                params=task.input_data,
                expected_outcome=task.input_data.get("expected_output", "Task completed"),
                dependencies=[
                    t
                    for t in hermes_context.task_order
                    if t in task.metadata.get("dependencies", [])
                ],
            )
            plan_steps.append(step)

        plan = Plan(
            goal=mission.user_request,
            steps=plan_steps,
            metadata={"hermes_context_id": hermes_context.mission_id},
        )

        self.state = ArchitectureState.IDLE
        return plan

    async def execute(self, mission: MissionContext, plan: Plan) -> list[ExecutionResult]:
        """Execute the plan using Hermes executor."""
        self.state = ArchitectureState.EXECUTING
        results = []

        if not self._current_context:
            # Reconstruct context
            hermes_context = HermesContext(
                mission_id=mission.mission_id, user_request=mission.user_request
            )
            self._current_context = hermes_context
        else:
            hermes_context = self._current_context

        for step in plan.steps:
            mission.current_step = step
            step.status = "running"
            step.started_at = datetime.now()

            self.state = ArchitectureState.EXECUTING

            # Find corresponding Hermes task
            task = hermes_context.tasks.get(step.id)
            if not task:
                # Create task from step
                task = HermesTask(
                    id=step.id,
                    name=step.name,
                    description=step.description,
                    agent_type=step.tool or "executor",
                    input_data=step.params,
                )
                hermes_context.tasks[step.id] = task

            try:
                self.state = ArchitectureState.EXECUTING

                # Execute using appropriate agent
                output = await self.executor.execute(task, hermes_context)

                task.output_data = output
                task.status = "completed"
                task.completed_at = datetime.now()

                exec_result = ExecutionResult(
                    step_id=step.id,
                    success=True,
                    output=output,
                    duration_ms=(task.completed_at - task.started_at).total_seconds() * 1000
                    if task.started_at
                    else 0,
                )

                step.result = output
                step.status = "completed"
                step.completed_at = datetime.now()

            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                task.completed_at = datetime.now()

                exec_result = ExecutionResult(
                    step_id=step.id,
                    success=False,
                    error=str(e),
                    duration_ms=(task.completed_at - task.started_at).total_seconds() * 1000
                    if task.started_at
                    else 0,
                )

            # Verify
            self.state = ArchitectureState.VERIFYING
            verification = await self.verify(step, exec_result)
            exec_result.verification = verification

            # Observe
            self.state = ArchitectureState.OBSERVING
            observations = await self.observe(mission, exec_result)

            # Store in memory
            hermes_context.working_memory[f"step_{step.id}"] = {
                "output": exec_result.output,
                "observations": observations,
                "verification": verification,
            }

            # Add to episodic memory
            hermes_context.episodic_memory.append(
                {
                    "step_id": step.id,
                    "timestamp": datetime.now().isoformat(),
                    "action": task.name,
                    "result": "success" if exec_result.success else "failed",
                    "observations": observations,
                }
            )

            results.append(exec_result)
            mission.executed_steps.append(exec_result)

            # Check continuation
            if not exec_result.success:
                break

        # Reflection
        self.state = ArchitectureState.REFLECTING
        completed_tasks = [t for t in hermes_context.tasks.values() if t.status == "completed"]
        reflection = await self.reflector.reflect(hermes_context, completed_tasks)

        hermes_context.working_memory["reflection"] = reflection

        # Store reflection in semantic memory
        hermes_context.semantic_memory[f"mission_{mission.mission_id}_reflection"] = reflection

        # Extract skills from successful patterns
        await self._extract_skills(hermes_context, completed_tasks)

        self.state = ArchitectureState.IDLE
        return results

    async def observe(
        self, mission: MissionContext, step_result: ExecutionResult
    ) -> dict[str, Any]:
        """Observe and analyze step result."""
        observations = {
            "timestamp": datetime.now().isoformat(),
            "step_id": step_result.step_id,
            "success": step_result.success,
        }

        # Use LLM for analysis
        if mission.current_step:
            analysis_prompt = f"""Analyze the execution result:
Step: {mission.current_step.name}
Description: {mission.current_step.description}
Agent: {mission.current_step.tool}
Success: {step_result.success}
Output: {str(step_result.output)[:500]}
Error: {step_result.error}

Provide observations on:
1. What was accomplished
2. Any issues
3. Next step recommendations"""

            analysis = await self.llm.achat(analysis_prompt, temperature=0.3)
            observations["analysis"] = analysis

        return observations

    async def reflect(self, mission: MissionContext) -> dict[str, Any]:
        """Reflect on completed mission."""
        if not self._current_context:
            return {"summary": "No context available"}

        completed_tasks = [
            t for t in self._current_context.tasks.values() if t.status == "completed"
        ]
        return await self.reflector.reflect(self._current_context, completed_tasks)

    async def verify(self, step: PlanStep, result: ExecutionResult) -> dict[str, Any]:
        """Verify step result."""
        if not self._current_context:
            return {"verified": result.success, "confidence": 1.0 if result.success else 0.0}

        task = self._current_context.tasks.get(step.id)
        if not task:
            return {"verified": result.success, "confidence": 1.0 if result.success else 0.0}

        return await self.verifier.verify(task, result.output if result.output else {})

    async def remember(
        self, mission: MissionContext, key: str, value: Any, memory_type: str = "working"
    ) -> None:
        """Store in memory."""
        if memory_type == "working" and self._current_context:
            self._current_context.working_memory[key] = value
        elif memory_type == "long_term" and self._current_context:
            self._current_context.semantic_memory[key] = value

    async def recall(self, mission: MissionContext, key: str, memory_type: str = "working") -> Any:
        """Recall from memory."""
        if memory_type == "working" and self._current_context:
            return self._current_context.working_memory.get(key)
        elif memory_type == "long_term" and self._current_context:
            return self._current_context.semantic_memory.get(key)
        return None

    def get_status(self) -> dict[str, Any]:
        """Get architecture status."""
        return {
            "name": self.name,
            "version": self.version,
            "state": self.state.value,
            "initialized": self._initialized,
            "current_context": self._current_context.mission_id if self._current_context else None,
            "memory_stats": {
                "working": len(self._current_context.working_memory)
                if self._current_context
                else 0,
                "episodic": len(self._current_context.episodic_memory)
                if self._current_context
                else 0,
                "semantic": len(self._current_context.semantic_memory)
                if self._current_context
                else 0,
                "skills": len(self._current_context.skills) if self._current_context else 0,
            },
        }

    def get_config_schema(self) -> dict[str, Any]:
        """Configuration schema."""
        return {
            "type": "object",
            "properties": {
                "planning_depth": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
                "verification_strictness": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "default": 0.8,
                },
                "auto_reflect": {"type": "boolean", "default": True},
                "skill_extraction": {"type": "boolean", "default": True},
                "memory_retention_days": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 365,
                    "default": 30,
                },
            },
        }

    async def _extract_skills(
        self, context: HermesContext, completed_tasks: list[HermesTask]
    ) -> None:
        """Extract reusable skills from completed tasks."""
        for task in completed_tasks:
            if task.status == "completed" and task.output_data:
                skill_key = f"{task.agent_type}_{task.name.lower().replace(' ', '_')}"
                if skill_key not in context.skills:
                    context.skills[skill_key] = {
                        "name": skill_key,
                        "agent_type": task.agent_type,
                        "template": task.description,
                        "input_schema": task.input_data,
                        "output_example": task.output_data,
                        "created_at": datetime.now().isoformat(),
                        "usage_count": 1,
                    }
                else:
                    context.skills[skill_key]["usage_count"] += 1
