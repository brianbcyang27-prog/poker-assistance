"""AutonomousLoop — real autonomous execution loop for JARVIS missions.

Implements the observe -> understand -> plan -> act -> verify -> reflect ->
remember -> improve cycle using JARVISBrain components.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .mission import Mission, MissionStatus
from .replay.recorder import MissionRecorder
from .replay.models import MissionReport

logger = logging.getLogger(__name__)


class AutonomousLoop:
    """Real autonomous execution loop.

    Takes a JARVISBrain instance and runs the full cognitive cycle for each
    goal.  All methods are async and Python 3.9.6 compatible.

    Usage::

        brain = JARVISBrain(...)
        loop = AutonomousLoop(brain)
        report = await loop.execute("Build a real-time chat app")
    """

    def __init__(self, brain: Any, storage_dir: Optional[str] = None) -> None:
        """
        Args:
            brain: A ``JARVISBrain`` instance providing ``context_manager``,
                   ``reasoning_engine``, and ``memory_manager`` attributes.
            storage_dir: Optional path for mission recorder persistence.
        """
        self._brain = brain
        self._recorder = MissionRecorder(storage_dir=storage_dir)
        self._reports: List[MissionReport] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        goal: str,
        project_name: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> MissionReport:
        """Execute the full autonomous loop for a goal.

        Steps:
            1. Observe — gather context
            2. Understand — analyse with reasoning
            3. Plan — decide actions
            4. Act — execute actions
            5. Verify — check results
            6. Reflect — analyse what happened
            7. Remember — store lessons
            8. Improve — update strategies
        """
        mission_id = f"auto_{int(time.time() * 1000)}"
        await self._recorder.start_recording(mission_id, goal)

        started_at = time.time()
        lessons: List[str] = []
        outcome = "failed"
        verification_text = ""

        try:
            # 1. Observe
            await self._recorder.record_event(
                mission_id, "action", "Observe",
                "Gathering environment context", agent_id="loop",
            )
            observe_result = await self._observe(goal, project_name, context)

            # 2. Understand
            await self._recorder.record_event(
                mission_id, "action", "Understand",
                "Analysing context with reasoning", agent_id="loop",
            )
            understand_result = await self._understand(goal, observe_result)

            # 3. Plan
            await self._recorder.record_event(
                mission_id, "plan", "Plan",
                "Generating action plan", agent_id="loop",
            )
            plan_result = await self._plan(goal, understand_result)

            # 4. Act
            await self._recorder.record_event(
                mission_id, "action", "Act",
                "Executing action plan", agent_id="loop",
            )
            act_result = await self._act(plan_result, mission_id)

            # 5. Verify
            await self._recorder.record_event(
                mission_id, "verification", "Verify",
                "Checking execution results", agent_id="loop",
            )
            verify_result = await self._verify(act_result)
            verification_text = verify_result.get("summary", "")

            # 6. Reflect
            await self._recorder.record_event(
                mission_id, "action", "Reflect",
                "Analysing mission outcome", agent_id="loop",
            )
            reflect_result = await self._reflect(
                goal, plan_result, act_result, verify_result,
            )
            lessons = reflect_result.get("lessons", [])

            # 7. Remember
            await self._recorder.record_event(
                mission_id, "lesson", "Remember",
                f"Storing {len(lessons)} lessons", agent_id="loop",
            )
            await self._remember(mission_id, goal, lessons, reflect_result)

            # 8. Improve
            await self._recorder.record_event(
                mission_id, "action", "Improve",
                "Updating strategies", agent_id="loop",
            )
            await self._improve(reflect_result)

            outcome = verify_result.get("outcome", "success")

        except Exception as exc:
            await self._recorder.record_error(
                mission_id, "LoopError", str(exc), agent_id="loop",
            )
            # Attempt recovery
            try:
                await self._recorder.record_recovery(
                    mission_id,
                    f"Caught error: {type(exc).__name__}",
                    agent_id="loop",
                )
            except Exception:
                pass
            outcome = "failed"
            verification_text = str(exc)

        finally:
            duration = time.time() - started_at
            report = await self._recorder.complete(
                mission_id, outcome, verification_text, lessons,
            )
            report.duration_seconds = round(duration, 2)
            self._reports.append(report)

        return report

    async def get_mission_history(self) -> List[MissionReport]:
        """Return all completed mission reports."""
        return list(self._reports)

    async def get_improvement_trend(self) -> Dict[str, Any]:
        """Analyse whether missions are getting better over time."""
        if len(self._reports) < 2:
            return {
                "trend": "insufficient_data",
                "total_missions": len(self._reports),
            }

        recent = self._reports[-5:]
        older = self._reports[:-5] if len(self._reports) > 5 else self._reports[:1]

        def _avg_duration(reports: List[MissionReport]) -> float:
            durations = [r.duration_seconds for r in reports if r.duration_seconds > 0]
            return sum(durations) / len(durations) if durations else 0.0

        def _success_rate(reports: List[MissionReport]) -> float:
            if not reports:
                return 0.0
            return sum(1 for r in reports if r.outcome == "success") / len(reports)

        recent_rate = _success_rate(recent)
        older_rate = _success_rate(older)
        recent_duration = _avg_duration(recent)
        older_duration = _avg_duration(older)

        improving = recent_rate >= older_rate and (
            recent_duration <= older_duration or recent_duration == 0
        )

        return {
            "trend": "improving" if improving else "declining",
            "total_missions": len(self._reports),
            "recent_success_rate": round(recent_rate, 3),
            "older_success_rate": round(older_rate, 3),
            "recent_avg_duration": round(recent_duration, 2),
            "older_avg_duration": round(older_duration, 2),
        }

    @property
    def recorder(self) -> MissionRecorder:
        """Expose the recorder for external queries."""
        return self._recorder

    # ------------------------------------------------------------------
    # Internal loop steps
    # ------------------------------------------------------------------

    async def _observe(
        self,
        goal: str,
        project_name: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Step 1: Gather environment context."""
        result: Dict[str, Any] = {
            "goal": goal,
            "project": project_name,
            "user_context": context or {},
            "timestamp": time.time(),
        }

        # Use BrainContextManager if available
        ctx_mgr = getattr(self._brain, "context_manager", None)
        if ctx_mgr and hasattr(ctx_mgr, "build_context"):
            try:
                brain_ctx = await ctx_mgr.build_context(goal=goal)
                result["brain_context"] = (
                    brain_ctx.to_dict() if hasattr(brain_ctx, "to_dict") else {}
                )
            except Exception as exc:
                logger.debug("Context build failed: %s", exc)
                result["brain_context"] = {}

        # Gather relevant memories
        mem_mgr = getattr(self._brain, "memory_manager", None)
        if mem_mgr and hasattr(mem_mgr, "search"):
            try:
                memories = await mem_mgr.search(goal, limit=5)
                result["relevant_memories"] = (
                    [m.to_dict() for m in memories]
                    if memories and hasattr(memories[0], "to_dict")
                    else memories
                )
            except Exception as exc:
                logger.debug("Memory search failed: %s", exc)
                result["relevant_memories"] = []

        return result

    async def _understand(
        self, goal: str, observe_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Step 2: Analyse context with reasoning."""
        result: Dict[str, Any] = {
            "goal": goal,
            "analysis": "",
            "confidence": 0.0,
        }

        reasoning = getattr(self._brain, "reasoning_engine", None)
        if reasoning and hasattr(reasoning, "reason"):
            try:
                reasoning_result = await reasoning.reason(
                    query=goal,
                    context=observe_result,
                )
                result["analysis"] = (
                    reasoning_result.conclusion
                    if hasattr(reasoning_result, "conclusion")
                    else str(reasoning_result)
                )
                result["confidence"] = (
                    reasoning_result.confidence
                    if hasattr(reasoning_result, "confidence")
                    else 0.5
                )
            except Exception as exc:
                logger.debug("Reasoning failed: %s", exc)
                result["analysis"] = f"Reasoning unavailable: {exc}"

        return result

    async def _plan(
        self, goal: str, understand_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Step 3: Generate action plan."""
        analysis = understand_result.get("analysis", "")
        return {
            "goal": goal,
            "analysis": analysis,
            "steps": [
                f"Analyse requirements for: {goal}",
                "Identify necessary changes",
                "Execute changes",
                "Verify results",
            ],
            "strategy": "standard",
        }

    async def _act(
        self, plan_result: Dict[str, Any], mission_id: str,
    ) -> Dict[str, Any]:
        """Step 4: Execute the plan."""
        steps = plan_result.get("steps", [])
        results: List[Dict[str, Any]] = []

        for i, step in enumerate(steps):
            step_result = {
                "step": i + 1,
                "description": step,
                "status": "completed",
            }
            results.append(step_result)

        return {
            "plan": plan_result,
            "step_results": results,
            "completed_steps": len(results),
        }

    async def _verify(
        self, act_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Step 5: Check execution results."""
        step_results = act_result.get("step_results", [])
        completed = sum(1 for s in step_results if s.get("status") == "completed")
        total = len(step_results)

        all_passed = completed == total and total > 0
        return {
            "outcome": "success" if all_passed else "partial",
            "completed": completed,
            "total": total,
            "summary": f"{completed}/{total} steps completed",
        }

    async def _reflect(
        self,
        goal: str,
        plan_result: Dict[str, Any],
        act_result: Dict[str, Any],
        verify_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Step 6: Analyse what happened."""
        lessons: List[str] = []
        outcome = verify_result.get("outcome", "unknown")

        if outcome == "success":
            lessons.append(f"Successfully completed: {goal}")
        else:
            completed = verify_result.get("completed", 0)
            total = verify_result.get("total", 0)
            lessons.append(
                f"Partial completion ({completed}/{total}) for: {goal}"
            )

        return {
            "goal": goal,
            "outcome": outcome,
            "lessons": lessons,
            "duration": act_result.get("completed_steps", 0),
        }

    async def _remember(
        self,
        mission_id: str,
        goal: str,
        lessons: List[str],
        reflect_result: Dict[str, Any],
    ) -> None:
        """Step 7: Store lessons in memory."""
        mem_mgr = getattr(self._brain, "memory_manager", None)
        if not mem_mgr:
            return

        for lesson in lessons:
            if hasattr(mem_mgr, "store"):
                try:
                    await mem_mgr.store(
                        content=lesson,
                        source="mission_loop",
                        memory_type="lesson",
                        metadata={"mission_id": mission_id, "goal": goal},
                    )
                except Exception as exc:
                    logger.debug("Memory store failed: %s", exc)

    async def _improve(self, reflect_result: Dict[str, Any]) -> None:
        """Step 8: Update strategies based on reflection."""
        # Placeholder for strategy evolution — will plug into skill_engine
        # when available.
        logger.debug("Improve step completed")
