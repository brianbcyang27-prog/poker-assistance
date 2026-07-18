"""Mission Pipeline — Autonomous Research & Execution Engine.

The pipeline orchestrates all 10 stages of a mission:
  1. Understand Goal
  2. Research
  3. Tool Discovery
  4. Architecture Planning
  5. Execution
  6. Verification
  7. Testing
  8. Self Review
  9. Memory Update
  10. Skill Evolution + Final Report

Never jump to coding. Research first.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Callable, List
from datetime import datetime

from .mission import (
    Mission, MissionStatus, MissionStage,
    ResearchFinding, ToolCandidate, ArchitecturePlan,
    VerificationResult, ReviewItem, MissionMemory,
)

log = logging.getLogger("jarvis.mission")


class MissionPipeline:
    """Autonomous mission pipeline — plans like a senior engineer.

    Usage:
        pipeline = MissionPipeline()
        mission = await pipeline.run("Build a real-time chat app with WebSocket")
        print(mission.final_report)
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self._stages = {
            MissionStage.UNDERSTAND: self._stage_understand,
            MissionStage.RESEARCH: self._stage_research,
            MissionStage.DISCOVER: self._stage_discover,
            MissionStage.PLAN: self._stage_plan,
            MissionStage.EXECUTE: self._stage_execute,
            MissionStage.VERIFY: self._stage_verify,
            MissionStage.TEST: self._stage_test,
            MissionStage.REVIEW: self._stage_review,
            MissionStage.MEMORY: self._stage_memory,
            MissionStage.EVOLVE: self._stage_evolve,
        }
        self._stage_order = [
            MissionStage.UNDERSTAND,
            MissionStage.RESEARCH,
            MissionStage.DISCOVER,
            MissionStage.PLAN,
            MissionStage.EXECUTE,
            MissionStage.VERIFY,
            MissionStage.TEST,
            MissionStage.REVIEW,
            MissionStage.MEMORY,
            MissionStage.EVOLVE,
        ]
        # Pluggable engines (set these to inject real implementations)
        self.research_engine = None
        self.discovery_engine = None
        self.planner_engine = None
        self.execution_engine = None
        self.verification_engine = None
        self.testing_engine = None
        self.review_engine = None
        self.memory_engine = None
        self.skill_engine = None

    async def run(self, user_request: str, priority: str = "normal") -> Mission:
        """Execute the full mission pipeline.

        Args:
            user_request: The user's request
            priority: Mission priority

        Returns:
            Completed Mission with all outputs
        """
        mission = Mission(user_request=user_request, priority=priority)
        mission.status = MissionStatus.RESEARCHING
        mission.started_at = datetime.now()

        log.info(f"Mission {mission.id} started: {user_request[:100]}")

        try:
            for stage in self._stage_order:
                mission.stage_start(stage.value)

                stage_handler = self._stages.get(stage)
                if not stage_handler:
                    continue

                try:
                    await stage_handler(mission)
                    mission.stage_complete(stage.value)
                    log.info(f"Mission {mission.id}: {stage.value} complete")

                except Exception as e:
                    mission.add_error(f"Stage {stage.value} failed: {str(e)}")
                    log.error(f"Mission {mission.id}: {stage.value} failed: {e}")

                    # Try to continue with remaining stages
                    if stage in (MissionStage.EXECUTE, MissionStage.VERIFY):
                        # Critical stages — pause and report
                        mission.status = MissionStatus.PAUSED
                        mission.add_error(f"Critical failure in {stage.value}. Mission paused.")
                        break

            # Generate final report
            self._generate_report(mission)

            if mission.status != MissionStatus.PAUSED:
                mission.status = MissionStatus.COMPLETED

        except Exception as e:
            mission.status = MissionStatus.FAILED
            mission.add_error(f"Pipeline failed: {str(e)}")
            log.error(f"Mission {mission.id} failed: {e}")

        finally:
            mission.completed_at = datetime.now()
            if mission.started_at:
                mission.duration_ms = (mission.completed_at - mission.started_at).total_seconds() * 1000

        return mission

    # ── Stage Implementations ──────────────────────────────

    async def _stage_understand(self, mission: Mission):
        """Stage 1: Understand the goal."""
        # Parse user request into structured goal
        mission.goal = mission.user_request

        # Extract key aspects
        if self.research_engine and hasattr(self.research_engine, 'understand_goal'):
            understanding = await self.research_engine.understand_goal(mission.user_request)
            mission.goal = understanding.get("goal", mission.user_request)

    async def _stage_research(self, mission: Mission):
        """Stage 2: Research existing solutions."""
        if not self.research_engine:
            log.debug("No research engine — skipping research stage")
            return

        # Research across multiple sources
        sources = [
            "github", "pypi", "npm", "docs", "stackoverflow",
            "awesome_lists", "huggingface", "docker",
        ]

        for source in sources:
            try:
                findings = await self.research_engine.search(
                    query=mission.goal,
                    source=source,
                )
                mission.research_findings.extend(findings)
            except Exception as e:
                log.debug(f"Research {source} failed: {e}")

        # Sort by relevance
        mission.research_findings.sort(key=lambda f: f.relevance, reverse=True)

    async def _stage_discover(self, mission: Mission):
        """Stage 3: Discover tools and libraries."""
        if not self.discovery_engine:
            log.debug("No discovery engine — skipping discovery stage")
            return

        try:
            candidates = await self.discovery_engine.discover(
                query=mission.goal,
                findings=mission.research_findings,
            )
            mission.tool_candidates = candidates
        except Exception as e:
            log.debug(f"Tool discovery failed: {e}")

    async def _stage_plan(self, mission: Mission):
        """Stage 4: Architecture planning."""
        if not self.planner_engine:
            log.debug("No planner engine — skipping planning stage")
            return

        try:
            plan = await self.planner_engine.create_plan(
                goal=mission.goal,
                research=mission.research_findings,
                tools=mission.tool_candidates,
            )
            mission.architecture_plan = plan
        except Exception as e:
            log.debug(f"Planning failed: {e}")

    async def _stage_execute(self, mission: Mission):
        """Stage 5: Execute the plan."""
        if not self.execution_engine:
            log.debug("No execution engine — skipping execution stage")
            return

        mission.status = MissionStatus.EXECUTING

        try:
            results = await self.execution_engine.execute(
                plan=mission.architecture_plan,
                mission=mission,
            )
            mission.execution_results = results
        except Exception as e:
            mission.add_error(f"Execution failed: {e}")
            raise

    async def _stage_verify(self, mission: Mission):
        """Stage 6: Verify the implementation."""
        if not self.verification_engine:
            log.debug("No verification engine — skipping verification stage")
            return

        mission.status = MissionStatus.VERIFYING

        try:
            results = await self.verification_engine.verify(
                mission=mission,
                execution_results=mission.execution_results,
            )
            mission.verification_results = results

            # Auto-repair if verification fails
            failed = [v for v in results if not v.passed]
            if failed and self.execution_engine:
                for retry in range(self.max_retries):
                    log.info(f"Verification failed ({len(failed)} checks). Auto-repair attempt {retry + 1}")
                    try:
                        repair_results = await self.execution_engine.repair(
                            failed_checks=failed,
                            mission=mission,
                        )
                        mission.execution_results.extend(repair_results)

                        # Re-verify
                        results = await self.verification_engine.verify(
                            mission=mission,
                            execution_results=mission.execution_results,
                        )
                        mission.verification_results = results
                        failed = [v for v in results if not v.passed]
                        if not failed:
                            break
                    except Exception as e:
                        log.debug(f"Auto-repair attempt {retry + 1} failed: {e}")

        except Exception as e:
            mission.add_error(f"Verification failed: {e}")

    async def _stage_test(self, mission: Mission):
        """Stage 7: Automated testing."""
        if not self.testing_engine:
            log.debug("No testing engine — skipping testing stage")
            return

        try:
            test_results = await self.testing_engine.test(mission=mission)
            mission.execution_results.extend(test_results)
        except Exception as e:
            log.debug(f"Testing failed: {e}")

    async def _stage_review(self, mission: Mission):
        """Stage 8: Self review."""
        if not self.review_engine:
            log.debug("No review engine — skipping review stage")
            return

        mission.status = MissionStatus.REVIEWING

        try:
            review_items = await self.review_engine.review(mission=mission)
            mission.review_items = review_items
        except Exception as e:
            log.debug(f"Review failed: {e}")

    async def _stage_memory(self, mission: Mission):
        """Stage 9: Update memory with mission learnings."""
        if not self.memory_engine:
            log.debug("No memory engine — skipping memory stage")
            return

        try:
            memory_record = await self.memory_engine.store_mission(mission=mission)
            mission.memory_record = memory_record
        except Exception as e:
            log.debug(f"Memory update failed: {e}")

    async def _stage_evolve(self, mission: Mission):
        """Stage 10: Skill evolution — learn for next time."""
        if not self.skill_engine:
            log.debug("No skill engine — skipping evolution stage")
            return

        try:
            await self.skill_engine.evolve(mission=mission)
        except Exception as e:
            log.debug(f"Skill evolution failed: {e}")

    # ── Report Generation ──────────────────────────────────

    def _generate_report(self, mission: Mission):
        """Generate the final mission report."""
        lines = [f"# Mission Report: {mission.id}\n"]
        lines.append(f"**Request:** {mission.user_request}\n")
        lines.append(f"**Status:** {mission.status}\n")
        lines.append(f"**Duration:** {mission.duration_ms:.0f}ms\n")

        # Research summary
        if mission.research_findings:
            lines.append(f"\n## Research ({len(mission.research_findings)} findings)\n")
            for f in mission.research_findings[:5]:
                lines.append(f"- **{f.title}** ({f.source}) — {f.description[:100]}")

        # Tool candidates
        if mission.tool_candidates:
            lines.append(f"\n## Tools Discovered ({len(mission.tool_candidates)})\n")
            for t in mission.tool_candidates[:5]:
                lines.append(f"- **{t.name}** ({t.source}) — score: {t.score:.2f}")

        # Architecture
        if mission.architecture_plan:
            plan = mission.architecture_plan
            lines.append(f"\n## Architecture\n")
            lines.append(f"- **Modules:** {len(plan.modules)}")
            lines.append(f"- **Files to modify:** {len(plan.files_to_modify)}")
            lines.append(f"- **New files:** {len(plan.new_files)}")
            lines.append(f"- **Risks:** {len(plan.risks)}")
            lines.append(f"- **Estimated hours:** {plan.estimated_hours}")

        # Verification
        if mission.verification_results:
            passed = sum(1 for v in mission.verification_results if v.passed)
            total = len(mission.verification_results)
            lines.append(f"\n## Verification: {passed}/{total} passed\n")
            for v in mission.verification_results:
                icon = "✓" if v.passed else "✗"
                lines.append(f"- {icon} {v.check_type}: {v.evidence[:80]}")

        # Review
        if mission.review_items:
            lines.append(f"\n## Self Review ({len(mission.review_items)} items)\n")
            for item in mission.review_items:
                lines.append(f"- **{item.category}**: {item.description}")

        # Errors
        if mission.errors:
            lines.append(f"\n## Errors ({len(mission.errors)})\n")
            for err in mission.errors:
                lines.append(f"- {err}")

        mission.final_report = "\n".join(lines)
