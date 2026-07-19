"""JARVIS Decision Memory — records, queries, and evolves past decisions.

Usage:
    engine = DecisionEngine()
    decision = await engine.record(
        title="Use FastAPI",
        reason="Async support",
        chosen_option="fastapi",
        alternatives=["flask", "django"],
    )
    active = await engine.get_active()
    await engine.supersede(decision.id, "Use Litestar", "Better DX", "litestar")
"""

from .engine import DecisionEngine
from .models import Decision, DecisionImpact, DecisionQuery, DecisionStatus

__all__ = [
    "DecisionEngine",
    "Decision",
    "DecisionImpact",
    "DecisionQuery",
    "DecisionStatus",
]
