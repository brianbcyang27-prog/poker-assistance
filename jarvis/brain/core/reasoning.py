"""Reasoning engine — evidence-based reasoning chain with memory integration."""
import logging
import time
from typing import Any, Dict, List, Optional

from .models import BrainContext, MemoryEntry, ReasoningResult

logger = logging.getLogger(__name__)


class ReasoningEngine:
    """Performs structured reasoning using context, memories, and decision history."""

    def __init__(self, memory_manager=None) -> None:
        self._memory = memory_manager
        self._history: List[ReasoningResult] = []

    async def reason(
        self, goal: str, context: BrainContext
    ) -> ReasoningResult:
        """Build a reasoning chain toward the goal using available context."""
        chain: List[str] = []
        warnings: List[str] = []
        supporting: List[str] = []
        alternatives: List[Dict[str, Any]] = []

        chain.append(f"Goal: {goal}")

        if context.user_preferences:
            chain.append(
                f"Considering {len(context.user_preferences)} user preferences"
            )
            for k, v in list(context.user_preferences.items())[:3]:
                chain.append(f"  Preference: {k}={v}")

        if context.relevant_memories:
            chain.append(
                f"Incorporating {len(context.relevant_memories)} relevant memories"
            )
            for m in context.relevant_memories[:3]:
                supporting.append(m.get("content", m.get("id", ""))[:100])

        if context.previous_attempts:
            chain.append(
                f"Found {len(context.previous_attempts)} previous attempts"
            )
            for a in context.previous_attempts[:3]:
                status = "succeeded" if a.get("outcome") else "pending"
                chain.append(
                    f"  Previous: {a.get('title', 'unknown')} ({status})"
                )
                alternatives.append({
                    "title": a.get("title", ""),
                    "reason": a.get("reason", ""),
                    "status": status,
                })

        if context.recent_decisions:
            chain.append(
                f"Reviewing {len(context.recent_decisions)} recent decisions"
            )

        if context.timeline_events:
            chain.append(
                f"Context includes {len(context.timeline_events)} timeline events"
            )

        if context.confidence < 0.5:
            warnings.append(
                f"Low context confidence ({context.confidence:.0%}) — limited information available"
            )

        if not context.relevant_memories and not context.previous_attempts:
            warnings.append("No prior memories or attempts found — fresh territory")

        confidence = context.confidence
        if supporting:
            confidence = min(confidence + 0.1, 1.0)
        if warnings:
            confidence = max(confidence - 0.1, 0.0)

        chain.append(f"Conclusion: proceeding with {confidence:.0%} confidence")

        result = ReasoningResult(
            conclusion=f"Pursue: {goal}",
            confidence=confidence,
            reasoning_chain=chain,
            alternatives=alternatives,
            supporting_memories=supporting,
            warnings=warnings,
        )
        self._history.append(result)
        return result

    async def analyze_options(
        self, options: List[Dict[str, Any]], criteria: List[str]
    ) -> List[Dict[str, Any]]:
        """Rank options against criteria, returning scored and sorted list."""
        scored: List[Dict[str, Any]] = []
        for opt in options:
            score = 0.0
            matches: List[str] = []
            for c in criteria:
                c_lower = c.lower()
                opt_text = " ".join(str(v) for v in opt.values()).lower()
                if c_lower in opt_text:
                    score += 1.0
                    matches.append(c)
            opt_scored = dict(opt)
            opt_scored["score"] = score / max(len(criteria), 1)
            opt_scored["criteria_matched"] = matches
            scored.append(opt_scored)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    async def assess_risk(
        self, action: str, context: BrainContext
    ) -> Dict[str, Any]:
        """Evaluate risk level for a proposed action."""
        risk_level = "low"
        factors: List[str] = []

        if context.confidence < 0.3:
            risk_level = "high"
            factors.append("Very low context confidence")
        elif context.confidence < 0.6:
            risk_level = "medium"
            factors.append("Moderate context confidence")

        if not context.relevant_memories:
            if risk_level == "low":
                risk_level = "medium"
            factors.append("No related memories found")

        if context.previous_attempts:
            failed = [
                a for a in context.previous_attempts
                if a.get("outcome") and "fail" in a.get("outcome", "").lower()
            ]
            if failed:
                risk_level = "high"
                factors.append(f"{len(failed)} previous failed attempts")

        return {
            "action": action,
            "risk_level": risk_level,
            "factors": factors,
            "confidence": context.confidence,
            "recommendation": (
                "Proceed" if risk_level == "low"
                else "Proceed with caution" if risk_level == "medium"
                else "Reconsider or get user approval"
            ),
        }

    async def explain_decision(
        self, decision_id: str, decisions_engine
    ) -> str:
        """Generate a natural-language explanation of why a decision was made."""
        if not decisions_engine:
            return "No decision engine available to explain."

        try:
            decision = await decisions_engine.get(decision_id)
            if not decision:
                return f"Decision {decision_id} not found."

            parts = [
                f"Decision: {decision.title}",
                f"Reason: {decision.reason}" if decision.reason else "",
                f"Chosen option: {decision.chosen_option}" if decision.chosen_option else "",
            ]
            if decision.alternatives:
                parts.append(f"Alternatives considered: {', '.join(decision.alternatives)}")
            if decision.outcome:
                parts.append(f"Outcome: {decision.outcome}")

            return "\n".join(p for p in parts if p)
        except Exception as exc:
            return f"Failed to explain decision: {exc}"

    def get_reasoning_history(self) -> List[ReasoningResult]:
        """Return the full history of reasoning operations."""
        return list(self._history)
