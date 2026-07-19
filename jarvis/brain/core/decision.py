"""Brain-level decision engine — decides, records, explains, and learns."""
import logging
import time
from typing import Any, Dict, List, Optional

from .models import ActionDecision, BrainContext, MemoryEntry

logger = logging.getLogger(__name__)


class BrainDecisionEngine:
    """High-level decision engine that integrates memory and reasoning."""

    def __init__(
        self,
        memory_manager=None,
        reasoning_engine=None,
        decisions_engine=None,
    ) -> None:
        self._memory = memory_manager
        self._reasoning = reasoning_engine
        self._decisions = decisions_engine
        self._action_history: Dict[str, ActionDecision] = {}

    async def decide(
        self,
        goal: str,
        context: BrainContext,
        options: Optional[List[Dict[str, Any]]] = None,
    ) -> ActionDecision:
        """Evaluate options and return the best action decision."""
        if not options:
            options = [{"action": "proceed", "reason": "default action"}]

        if self._reasoning and len(options) > 1:
            criteria = ["goal", "preference", "memory", "context"]
            ranked = await self._reasoning.analyze_options(options, criteria)
        else:
            ranked = [{"action": o.get("action", "unknown"), "score": 0.5, **o} for o in options]

        best = ranked[0] if ranked else options[0]
        rejected = [r for r in ranked[1:]] if len(ranked) > 1 else []

        supporting: List[str] = []
        if context.relevant_memories:
            supporting.extend(
                m.get("content", "")[:100] for m in context.relevant_memories[:3]
            )

        risk_level = "low"
        if self._reasoning:
            risk = await self._reasoning.assess_risk(
                best.get("action", ""), context
            )
            risk_level = risk.get("risk_level", "low")

        decision = ActionDecision(
            action=best.get("action", best.get("reason", "proceed")),
            reason=best.get("reason", best.get("description", "")),
            confidence=best.get("score", context.confidence),
            alternatives_rejected=rejected,
            supporting_evidence=supporting,
            risk_level=risk_level,
        )

        self._action_history[decision.id] = decision

        if self._decisions:
            try:
                await self._decisions.record(
                    title=decision.action,
                    description=decision.reason,
                    reason=decision.reason,
                    impact=decision.risk_level,
                    related_entities=[goal],
                )
            except Exception as exc:
                logger.debug("Failed to record decision in decisions engine: %s", exc)

        logger.debug(
            "Decision made: %s (confidence=%.2f, risk=%s)",
            decision.action[:60], decision.confidence, decision.risk_level,
        )
        return decision

    async def explain(self, decision_id: str) -> str:
        """Return a natural-language explanation of a decision."""
        decision = self._action_history.get(decision_id)
        if not decision:
            if self._decisions:
                try:
                    return await self._reasoning.explain_decision(
                        decision_id, self._decisions
                    ) if self._reasoning else f"Decision {decision_id} not found."
                except Exception:
                    pass
            return f"Decision {decision_id} not found."

        parts = [
            f"Action: {decision.action}",
            f"Reason: {decision.reason}" if decision.reason else "",
            f"Confidence: {decision.confidence:.0%}",
            f"Risk: {decision.risk_level}",
        ]
        if decision.alternatives_rejected:
            parts.append(
                f"Alternatives rejected: {len(decision.alternatives_rejected)}"
            )
        if decision.supporting_evidence:
            parts.append(f"Supporting evidence: {len(decision.supporting_evidence)} items")

        return "\n".join(p for p in parts if p)

    async def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        success: bool,
    ) -> Dict[str, Any]:
        """Record the outcome of a previously made decision."""
        decision = self._action_history.get(decision_id)
        if not decision:
            return {"ok": False, "error": f"Decision {decision_id} not found"}

        result = {
            "ok": True,
            "decision_id": decision_id,
            "outcome": outcome,
            "success": success,
        }

        if self._decisions:
            try:
                all_d = await self._decisions.get_recent(n=50)
                for d in all_d:
                    if d.title == decision.action:
                        await self._decisions.update_outcome(d.id, outcome)
                        break
            except Exception as exc:
                logger.debug("Failed to update outcome in decisions engine: %s", exc)

        if self._memory and not success:
            try:
                await self._memory.remember(
                    content=f"Decision '{decision.action}' failed: {outcome}",
                    memory_type="lesson",
                    importance="important",
                    source="decision_outcome",
                    metadata={"decision_id": decision_id, "success": False},
                )
            except Exception as exc:
                logger.debug("Failed to record lesson: %s", exc)

        return result

    async def get_decision_history(
        self, limit: int = 20
    ) -> List[ActionDecision]:
        """Return the most recent action decisions."""
        sorted_d = sorted(
            self._action_history.values(),
            key=lambda d: d.timestamp,
            reverse=True,
        )
        return sorted_d[:limit]

    async def learn_from_mistake(
        self, decision_id: str, lesson: str
    ) -> Dict[str, Any]:
        """Extract a lesson from a failed decision."""
        decision = self._action_history.get(decision_id)
        if not decision:
            return {"ok": False, "error": f"Decision {decision_id} not found"}

        if self._memory:
            try:
                await self._memory.remember(
                    content=lesson,
                    memory_type="lesson",
                    importance="important",
                    source="mistake_learning",
                    metadata={
                        "decision_id": decision_id,
                        "original_action": decision.action,
                    },
                )
            except Exception as exc:
                logger.debug("Failed to store lesson in memory: %s", exc)
                return {"ok": False, "error": str(exc)}

        return {"ok": True, "decision_id": decision_id, "lesson": lesson}
