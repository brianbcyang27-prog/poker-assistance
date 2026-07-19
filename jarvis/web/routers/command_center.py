"""Command Center API — unified endpoints for the v5.5.0 command center UI.

Covers missions, brain, agents, tools, and self-reflection data.
"""

import time
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from jarvis.web.rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["command-center"])


# ── Helpers ────────────────────────────────────────────────────

def _safe(fn, default=None):
    """Call *fn* and return its result, or *default* on any exception."""
    try:
        return fn()
    except Exception as exc:
        logger.debug("command_center._safe: %s", exc)
        return default


def _serialize(obj):
    """Best-effort serialisation for dataclass / pydantic objects."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)


# ═══════════════════════════════════════════════════════════════
#  MISSIONS
# ═══════════════════════════════════════════════════════════════

def _get_mission_manager():
    from jarvis.mission.manager import MissionManager
    return MissionManager()


@router.get("/missions")
async def list_missions(status: Optional[str] = None, limit: int = 50):
    """List all missions, optionally filtered by status."""
    mm = _get_mission_manager()
    try:
        await mm.load()
    except Exception:
        pass

    if status == "active":
        missions = await mm.list_active()
    elif status in ("completed", "failed"):
        missions = await mm.list_completed()
    else:
        missions = list(mm._missions.values())

    missions = sorted(missions, key=lambda m: m.created_at, reverse=True)[:limit]
    return {
        "missions": [_serialize(m) for m in missions],
        "total": len(missions),
    }


@router.get("/missions/stats")
async def mission_stats():
    """Aggregate mission statistics."""
    mm = _get_mission_manager()
    try:
        await mm.load()
    except Exception:
        pass

    all_missions = list(mm._missions.values())
    completed = [m for m in all_missions if m.status == "completed"]
    failed = [m for m in all_missions if m.status == "failed"]
    active_statuses = {"created", "researching", "planning", "executing", "verifying", "reviewing", "paused"}
    active = [m for m in all_missions if m.status in active_statuses]

    durations = [m.duration_ms for m in completed if m.duration_ms > 0]
    avg_duration = sum(durations) / len(durations) if durations else 0

    return {
        "total": len(all_missions),
        "active": len(active),
        "completed": len(completed),
        "failed": len(failed),
        "avg_duration_ms": round(avg_duration, 1),
        "success_rate": round(len(completed) / max(len(completed) + len(failed), 1) * 100, 1),
    }


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str):
    """Get full detail for a single mission."""
    mm = _get_mission_manager()
    try:
        await mm.load()
    except Exception:
        pass

    mission = await mm.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    data = _serialize(mission)
    data["progress"] = await mm.get_progress(mission_id)
    data["eta_seconds"] = await mm.get_eta(mission_id)
    return data


@router.get("/missions/{mission_id}/timeline")
async def mission_timeline(mission_id: str):
    """Get the stage-history timeline for a mission."""
    mm = _get_mission_manager()
    try:
        await mm.load()
    except Exception:
        pass

    mission = await mm.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    return {
        "mission_id": mission_id,
        "timeline": mission.stage_history,
        "current_stage": mission.current_stage,
        "errors": mission.errors,
    }


@router.get("/missions/{mission_id}/replay")
async def mission_replay(mission_id: str):
    """Get the full replay text for a mission."""
    mm = _get_mission_manager()
    try:
        await mm.load()
    except Exception:
        pass

    mission = await mm.get(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    lines = [
        f"Mission: {mission.id}",
        f"Goal: {mission.goal}",
        f"Status: {mission.status}",
        f"Created: {mission.created_at}",
    ]
    if mission.started_at:
        lines.append(f"Started: {mission.started_at}")
    if mission.completed_at:
        lines.append(f"Completed: {mission.completed_at}")
    if mission.duration_ms:
        lines.append(f"Duration: {mission.duration_ms:.0f}ms")

    lines.append("")
    lines.append("=== Stage History ===")
    for entry in mission.stage_history:
        lines.append(f"  [{entry.get('action', '?')}] {entry.get('stage', '?')} @ {entry.get('timestamp', '?')}")

    if mission.execution_results:
        lines.append("")
        lines.append("=== Execution Results ===")
        for i, r in enumerate(mission.execution_results, 1):
            lines.append(f"  {i}. {r}")

    if mission.errors:
        lines.append("")
        lines.append("=== Errors ===")
        for e in mission.errors:
            lines.append(f"  - {e}")

    if mission.final_report:
        lines.append("")
        lines.append("=== Final Report ===")
        lines.append(mission.final_report)

    return {
        "mission_id": mission_id,
        "replay_text": "\n".join(lines),
    }


# ═══════════════════════════════════════════════════════════════
#  BRAIN
# ═══════════════════════════════════════════════════════════════

def _get_brain():
    from jarvis.brain.core.brain import JARVISBrain
    brain = JARVISBrain()
    return brain


@router.get("/brain/status")
async def brain_status():
    """Brain health and statistics."""
    brain = _get_brain()
    status = await brain.get_status()
    return status


@router.get("/brain/context")
async def brain_context(goal: str = "general status"):
    """Current brain context for a goal."""
    brain = _get_brain()
    ctx = await brain.think(goal)
    return {
        "goal": goal,
        "confidence": ctx.confidence,
        "preferences_count": len(ctx.user_preferences),
        "memories_count": len(ctx.relevant_memories),
        "attempts_count": len(ctx.previous_attempts),
        "decisions_count": len(ctx.recent_decisions),
        "events_count": len(ctx.timeline_events),
        "context": ctx.to_dict() if hasattr(ctx, "to_dict") else {},
    }


@router.get("/brain/decisions")
async def brain_decisions(limit: int = 20):
    """Recent decisions from the decision engine."""
    try:
        from jarvis.decisions.engine import DecisionEngine
        engine = DecisionEngine()
        await engine.load()
        decisions = await engine.get_recent(n=limit)
        return {
            "decisions": [d.to_dict() for d in decisions],
            "total": len(decisions),
        }
    except Exception as exc:
        return {"decisions": [], "total": 0, "error": str(exc)}


class ReasonRequest(BaseModel):
    goal: str = Field(..., description="The goal to reason about")
    project: str = Field("", description="Optional project name")


@router.post("/brain/reason")
@rate_limit(max_requests=5, window_seconds=60)
async def brain_reason(request: Request, req: ReasonRequest):
    """Request a reasoning chain for a goal."""
    brain = _get_brain()
    ctx = await brain.think(req.goal, project_name=req.project)
    result = await brain.reason(req.goal, ctx)
    return {
        "goal": req.goal,
        "conclusion": result.conclusion,
        "confidence": result.confidence,
        "chain": result.reasoning_chain,
        "alternatives": result.alternatives,
        "supporting_memories": result.supporting_memories,
        "warnings": result.warnings,
    }


# ═══════════════════════════════════════════════════════════════
#  AGENTS
# ═══════════════════════════════════════════════════════════════

def _get_jarvis():
    import jarvis.web.main as web_main
    return web_main.jarvis


@router.get("/agents/personas")
async def agent_personas():
    """List all agent personas with their metadata."""
    jarvis = _get_jarvis()
    if not jarvis:
        return {"personas": [], "error": "JARVIS not initialized"}

    personas = []

    # JARVIS itself
    personas.append({
        "card_id": "J",
        "name": "JARVIS",
        "role": "Orchestrator",
        "suit": None,
        "state": jarvis.state.value if hasattr(jarvis.state, "value") else str(jarvis.state),
        "type": "core",
    })

    for king in jarvis.get_all_kings():
        personas.append({
            "card_id": king.card_id,
            "name": king.name,
            "role": f"{king.suit.value.title()} King" if king.suit else "King",
            "suit": king.suit.value if king.suit else None,
            "state": king.state.value if hasattr(king.state, "value") else str(king.state),
            "type": "king",
            "workers": [
                {
                    "card_id": w.card_id,
                    "name": w.name,
                    "state": w.state.value if hasattr(w.state, "value") else str(w.state),
                }
                for w in king.get_all_workers()
            ],
        })

    return {"personas": personas, "total": len(personas)}


# ═══════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════

@router.get("/tools/availability")
async def tool_availability():
    """Status of all registered tools / capabilities."""
    try:
        from jarvis.core.capabilities import registry
        caps = await registry.query()
        tools = []
        for c in caps:
            tools.append({
                "name": c.name,
                "owner": c.owner,
                "type": c.type.value if hasattr(c.type, "value") else str(c.type),
                "description": c.description,
                "tags": c.tags,
                "available": True,
            })
        return {"tools": tools, "total": len(tools)}
    except Exception as exc:
        return {"tools": [], "total": 0, "error": str(exc)}


# ═══════════════════════════════════════════════════════════════
#  SELF-REFLECTION
# ═══════════════════════════════════════════════════════════════

@router.get("/self/errors")
async def self_errors(limit: int = 30):
    """Recent errors from across the system."""
    try:
        from jarvis.core.events import event_bus
        events = event_bus.get_history(event_type="worker.error", limit=limit)
        errors = [
            {
                "source": e.source,
                "type": e.type,
                "data": e.data,
                "timestamp": e.timestamp,
            }
            for e in events
        ]
        # Also pull mission errors
        mm = _get_mission_manager()
        try:
            await mm.load()
        except Exception:
            pass
        for m in list(mm._missions.values())[-limit:]:
            for err in m.errors:
                errors.append({
                    "source": m.id,
                    "type": "mission.error",
                    "data": {"error": err},
                    "timestamp": m.created_at.isoformat() if hasattr(m.created_at, "isoformat") else str(m.created_at),
                })

        errors.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return {"errors": errors[:limit], "total": len(errors)}
    except Exception as exc:
        return {"errors": [], "total": 0, "error": str(exc)}


@router.get("/self/lessons")
async def self_lessons(limit: int = 30):
    """Lessons learned from completed missions."""
    try:
        from jarvis.learning.engine import LearningEngine
        engine = LearningEngine()
        # Pull from knowledge base
        records = engine._knowledge_base[-limit:] if hasattr(engine, "_knowledge_base") else []
        lessons = [_serialize(r) for r in records]
        return {"lessons": lessons, "total": len(lessons)}
    except Exception as exc:
        return {"lessons": [], "total": 0, "error": str(exc)}
