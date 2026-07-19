"""Mission Replay API — v5.5.0 unified command center endpoints.

Covers missions, brain, agents, tools, and self-reflection data.
All endpoints use graceful fallbacks so the UI stays functional even
when subsystems are unavailable.
"""

import time
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["replay"])


# ── Helpers ────────────────────────────────────────────────────

def _safe(fn, default=None):
    """Call *fn* and return its result, or *default* on any exception."""
    try:
        return fn()
    except Exception as exc:
        logger.debug("mission_replay._safe: %s", exc)
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
    try:
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
    except Exception as exc:
        logger.warning("list_missions failed: %s", exc)
        return {"missions": [], "total": 0, "error": str(exc)}


@router.get("/missions/stats")
async def mission_stats():
    """Aggregate mission statistics."""
    try:
        mm = _get_mission_manager()
        try:
            await mm.load()
        except Exception:
            pass

        all_missions = list(mm._missions.values())
        completed = [m for m in all_missions if m.status == "completed"]
        failed = [m for m in all_missions if m.status == "failed"]
        active_statuses = {
            "created", "researching", "planning", "executing",
            "verifying", "reviewing", "paused",
        }
        active = [m for m in all_missions if m.status in active_statuses]

        durations = [m.duration_ms for m in completed if m.duration_ms and m.duration_ms > 0]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total": len(all_missions),
            "active": len(active),
            "completed": len(completed),
            "failed": len(failed),
            "avg_duration_ms": round(avg_duration, 1),
            "success_rate": round(
                len(completed) / max(len(completed) + len(failed), 1) * 100, 1
            ),
        }
    except Exception as exc:
        logger.warning("mission_stats failed: %s", exc)
        return {
            "total": 0, "active": 0, "completed": 0, "failed": 0,
            "avg_duration_ms": 0, "success_rate": 0, "error": str(exc),
        }


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str):
    """Get full detail for a single mission."""
    try:
        mm = _get_mission_manager()
        try:
            await mm.load()
        except Exception:
            pass

        mission = await mm.get(mission_id)
        if not mission:
            raise HTTPException(
                status_code=404, detail=f"Mission '{mission_id}' not found"
            )

        data = _serialize(mission)
        data["progress"] = _safe(lambda: mm.get_progress(mission_id), 0)
        data["eta_seconds"] = _safe(lambda: mm.get_eta(mission_id), None)
        return data
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("get_mission failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/missions/{mission_id}/timeline")
async def mission_timeline(mission_id: str):
    """Get the stage-history timeline for a mission."""
    try:
        mm = _get_mission_manager()
        try:
            await mm.load()
        except Exception:
            pass

        mission = await mm.get(mission_id)
        if not mission:
            raise HTTPException(
                status_code=404, detail=f"Mission '{mission_id}' not found"
            )

        return {
            "mission_id": mission_id,
            "timeline": mission.stage_history,
            "current_stage": mission.current_stage,
            "errors": mission.errors,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("mission_timeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/missions/{mission_id}/replay")
async def mission_replay(mission_id: str):
    """Get the full replay text for a mission."""
    try:
        mm = _get_mission_manager()
        try:
            await mm.load()
        except Exception:
            pass

        mission = await mm.get(mission_id)
        if not mission:
            raise HTTPException(
                status_code=404, detail=f"Mission '{mission_id}' not found"
            )

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
            action = entry.get("action", "?")
            stage = entry.get("stage", "?")
            ts = entry.get("timestamp", "?")
            lines.append(f"  [{action}] {stage} @ {ts}")

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
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("mission_replay failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ═══════════════════════════════════════════════════════════════
#  BRAIN
# ═══════════════════════════════════════════════════════════════

def _get_brain():
    from jarvis.brain.core.brain import JARVISBrain
    return JARVISBrain()


@router.get("/brain/status")
async def brain_status():
    """Brain health and statistics."""
    try:
        brain = _get_brain()
        status = await brain.get_status()
        return status
    except Exception as exc:
        logger.warning("brain_status failed: %s", exc)
        return {"status": "unavailable", "error": str(exc)}


@router.get("/brain/context")
async def brain_context(goal: str = "general status"):
    """Current brain context for a goal."""
    try:
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
    except Exception as exc:
        logger.warning("brain_context failed: %s", exc)
        return {
            "goal": goal, "confidence": 0,
            "preferences_count": 0, "memories_count": 0,
            "attempts_count": 0, "decisions_count": 0,
            "events_count": 0, "context": {}, "error": str(exc),
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
        logger.debug("brain_decisions: %s", exc)
        return {"decisions": [], "total": 0, "error": str(exc)}


class ReasonRequest(BaseModel):
    goal: str = Field(..., description="The goal to reason about")
    project: str = Field("", description="Optional project name")


@router.post("/brain/reason")
async def brain_reason(req: ReasonRequest):
    """Request a reasoning chain for a goal."""
    try:
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
    except Exception as exc:
        logger.warning("brain_reason failed: %s", exc)
        return {
            "goal": req.goal, "conclusion": None, "confidence": 0,
            "chain": [], "alternatives": [], "supporting_memories": [],
            "warnings": [str(exc)],
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
    try:
        jarvis = _get_jarvis()
        if not jarvis:
            return {"personas": [], "error": "JARVIS not initialized"}

        personas = []

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
    except Exception as exc:
        logger.warning("agent_personas failed: %s", exc)
        return {"personas": [], "total": 0, "error": str(exc)}


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
        logger.debug("tool_availability: %s", exc)
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

        try:
            mm = _get_mission_manager()
            try:
                await mm.load()
            except Exception:
                pass
            for m in list(mm._missions.values())[-limit:]:
                for err in m.errors:
                    ts = m.created_at
                    if hasattr(ts, "isoformat"):
                        ts = ts.isoformat()
                    errors.append({
                        "source": m.id,
                        "type": "mission.error",
                        "data": {"error": err},
                        "timestamp": str(ts),
                    })
        except Exception:
            pass

        errors.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return {"errors": errors[:limit], "total": len(errors)}
    except Exception as exc:
        logger.debug("self_errors: %s", exc)
        return {"errors": [], "total": 0, "error": str(exc)}


@router.get("/self/lessons")
async def self_lessons(limit: int = 30):
    """Lessons learned from completed missions."""
    try:
        from jarvis.learning.engine import LearningEngine
        engine = LearningEngine()
        records = engine._knowledge_base[-limit:] if hasattr(engine, "_knowledge_base") else []
        lessons = [_serialize(r) for r in records]
        return {"lessons": lessons, "total": len(lessons)}
    except Exception as exc:
        logger.debug("self_lessons: %s", exc)
        return {"lessons": [], "total": 0, "error": str(exc)}
