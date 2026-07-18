"""Self Review — Post-mission review and learning extraction.

Reviews the mission outcome, extracts lessons learned,
and identifies improvements for future missions.
"""

import logging
from typing import List, Dict, Any, Optional
from ..mission.mission import (
    Mission, ReviewItem, MissionStage,
)

log = logging.getLogger("jarvis.review")


class ReviewEngine:
    """Self-review engine — learns from every mission.

    After every mission, answers:
      1. What went well?
      2. What went wrong?
      3. What could be improved?
      4. What patterns emerged?
    """

    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    async def review(self, mission: Mission) -> List[ReviewItem]:
        """Review the mission outcome.

        Args:
            mission: Completed mission

        Returns:
            List of ReviewItem with findings
        """
        items = []

        # 1. Check research quality
        research_item = await self._review_research(mission)
        if research_item:
            items.append(research_item)

        # 2. Check planning quality
        plan_item = await self._review_planning(mission)
        if plan_item:
            items.append(plan_item)

        # 3. Check execution quality
        exec_item = await self._review_execution(mission)
        if exec_item:
            items.append(exec_item)

        # 4. Check verification quality
        verify_item = await self._review_verification(mission)
        if verify_item:
            items.append(verify_item)

        # 5. Check testing coverage
        test_item = await self._review_testing(mission)
        if test_item:
            items.append(test_item)

        # 6. Check error handling
        error_item = await self._review_errors(mission)
        if error_item:
            items.append(error_item)

        # 7. Duration analysis
        duration_item = await self._review_duration(mission)
        if duration_item:
            items.append(duration_item)

        # Store for pattern detection
        self._history.append({
            "mission_id": mission.id,
            "items": [item.category for item in items],
            "duration_ms": mission.duration_ms,
            "status": mission.status,
        })

        log.info(f"Review complete: {len(items)} items")
        return items

    # ── Review Checks ──────────────────────────────────────

    async def _review_research(self, mission: Mission) -> Optional[ReviewItem]:
        """Review research quality."""
        if not mission.research_findings:
            return ReviewItem(
                category="research",
                severity="warning",
                description="No research findings collected — may miss existing solutions",
                recommendation="Always research before coding. Check GitHub, PyPI, and docs.",
            )

        high_relevance = [f for f in mission.research_findings if f.relevance > 0.7]
        if not high_relevance:
            return ReviewItem(
                category="research",
                severity="info",
                description="Research found results but none with high relevance",
                recommendation="Refine search queries or check different sources.",
            )

        return None

    async def _review_planning(self, mission: Mission) -> Optional[ReviewItem]:
        """Review planning quality."""
        if not mission.architecture_plan:
            return ReviewItem(
                category="planning",
                severity="warning",
                description="No architecture plan created — jumping straight to coding",
                recommendation="Always create a plan first. Spend 30 minutes planning, save hours coding.",
            )

        plan = mission.architecture_plan
        if plan.estimated_hours > 20:
            return ReviewItem(
                category="planning",
                severity="warning",
                description=f"Plan estimates {plan.estimated_hours} hours — may be too ambitious",
                recommendation="Consider breaking into smaller milestones.",
            )

        return None

    async def _review_execution(self, mission: Mission) -> Optional[ReviewItem]:
        """Review execution quality."""
        if not mission.execution_results:
            return ReviewItem(
                category="execution",
                severity="info",
                description="No execution results — mission may not have been executed",
                recommendation="Ensure execution engine is connected.",
            )

        failed = [r for r in mission.execution_results if not r.get("success")]
        if failed:
            return ReviewItem(
                category="execution",
                severity="warning",
                description=f"{len(failed)} execution steps failed",
                recommendation="Review failed steps and consider manual intervention.",
            )

        return None

    async def _review_verification(self, mission: Mission) -> Optional[ReviewItem]:
        """Review verification quality."""
        if not mission.verification_results:
            return ReviewItem(
                category="verification",
                severity="warning",
                description="No verification performed — quality unknown",
                recommendation="Always verify implementations before marking complete.",
            )

        failed = [v for v in mission.verification_results if not v.passed]
        if failed:
            return ReviewItem(
                category="verification",
                severity="error",
                description=f"{len(failed)}/{len(mission.verification_results)} verification checks failed",
                recommendation="Fix failing checks before proceeding.",
            )

        return None

    async def _review_testing(self, mission: Mission) -> Optional[ReviewItem]:
        """Review testing coverage."""
        return None

    async def _review_errors(self, mission: Mission) -> Optional[ReviewItem]:
        """Review error handling."""
        if mission.errors:
            return ReviewItem(
                category="error_handling",
                severity="warning",
                description=f"{len(mission.errors)} errors occurred during mission",
                recommendation="Investigate root causes to prevent recurrence.",
            )
        return None

    async def _review_duration(self, mission: Mission) -> Optional[ReviewItem]:
        """Review mission duration."""
        if mission.duration_ms and mission.duration_ms > 300000:
            return ReviewItem(
                category="performance",
                severity="info",
                description=f"Mission took {mission.duration_ms / 1000:.1f}s — consider optimization",
                recommendation="Profile slow stages and optimize bottlenecks.",
            )
        return None

    def get_patterns(self) -> List[Dict[str, Any]]:
        """Analyze mission history for patterns."""
        if len(self._history) < 3:
            return []

        patterns = []

        # Common failure categories
        all_items = []
        for h in self._history:
            all_items.extend(h["items"])

        from collections import Counter
        item_counts = Counter(all_items)

        for item, count in item_counts.most_common(5):
            if count >= 2:
                patterns.append({
                    "type": "recurring_issue",
                    "category": item,
                    "frequency": count,
                    "suggestion": f"Improve {item} process — recurring issue across missions",
                })

        return patterns
