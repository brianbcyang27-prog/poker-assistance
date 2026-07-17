"""System router — Events, capabilities, and system status for v3.1."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/system", tags=["system"])


# ===== EVENTS =====

@router.get("/events")
async def get_events(event_type: Optional[str] = None, limit: int = 50):
    """Get recent events from the event bus."""
    from jarvis.core.events import event_bus
    events = event_bus.get_history(event_type=event_type, limit=limit)
    return {
        "events": [
            {
                "id": e.id,
                "type": e.type,
                "source": e.source,
                "data": e.data,
                "timestamp": e.timestamp,
            }
            for e in events
        ],
        "total": len(events),
    }


@router.get("/events/stats")
async def event_stats():
    """Get event bus statistics."""
    from jarvis.core.events import event_bus
    return event_bus.get_stats()


# ===== CAPABILITIES =====

@router.get("/capabilities")
async def list_capabilities(
    type: Optional[str] = None,
    owner: Optional[str] = None,
):
    """List all registered capabilities."""
    from jarvis.core.capabilities import registry, CapType
    cap_type = CapType(type) if type else None
    caps = await registry.query(type=cap_type, owner=owner)
    return {
        "capabilities": [c.to_dict() for c in caps],
        "total": len(caps),
    }


@router.get("/capabilities/stats")
async def capability_stats():
    """Get capability registry statistics."""
    from jarvis.core.capabilities import registry
    return await registry.get_stats()


@router.get("/capabilities/best")
async def find_best_capability(
    type: Optional[str] = None,
    owner: Optional[str] = None,
    description: str = "",
):
    """Find the best capability matching criteria."""
    from jarvis.core.capabilities import registry, CapType
    cap_type = CapType(type) if type else None
    best = await registry.find_best(type=cap_type, owner=owner, description=description)
    if not best:
        return {"found": False}
    return {"found": True, "capability": best.to_dict()}


class CapabilityRegister(BaseModel):
    name: str
    owner: str
    type: str
    description: str = ""
    version: str = "1.0.0"
    tags: list[str] = []


@router.post("/capabilities")
async def register_capability(req: CapabilityRegister):
    """Register a new capability."""
    from jarvis.core.capabilities import registry, Capability, CapType
    cap = Capability(
        name=req.name,
        owner=req.owner,
        type=CapType(req.type),
        description=req.description,
        version=req.version,
        tags=req.tags,
    )
    return await registry.register(cap)


# ===== MEMORY (pluggable) =====

@router.get("/memory/stats")
async def memory_stats():
    """Get memory provider statistics."""
    from jarvis.brain.memory_provider import get_memory
    mem = get_memory()
    return {
        "provider": type(mem).__name__,
        "total": await mem.count(),
        "types": await mem.list_types(),
    }


class MemoryStore(BaseModel):
    type: str
    content: str
    metadata: dict = {}
    source: str = ""
    tags: list[str] = []


@router.post("/memory/store")
async def store_memory(req: MemoryStore):
    """Store a memory entry."""
    from jarvis.brain.memory_provider import get_memory, MemoryEntry
    mem = get_memory()
    entry = MemoryEntry(
        type=req.type,
        content=req.content,
        metadata=req.metadata,
        source=req.source,
        tags=req.tags,
    )
    return await mem.store(entry)


@router.get("/memory/search")
async def search_memory(q: str, limit: int = 10):
    """Search memories using FTS5."""
    from jarvis.brain.memory_provider import get_memory
    mem = get_memory()
    results = await mem.search(q, limit=limit)
    return {
        "query": q,
        "results": [r.to_dict() for r in results],
        "total": len(results),
    }


# ===== MODEL ROUTER =====

@router.get("/models")
async def list_models():
    """List registered models and routing stats."""
    from jarvis.brain.model_router import router
    return router.get_routing_stats()


@router.get("/models/route")
async def route_model(
    task_type: Optional[str] = None,
    task_description: str = "",
    require_tools: bool = False,
):
    """Find the best model for a task."""
    from jarvis.brain.model_router import router, TaskType
    tt = TaskType(task_type) if task_type else None
    best = router.route(
        task_type=tt,
        task_description=task_description,
        require_tools=require_tools,
    )
    if not best:
        return {"found": False}
    return {"found": True, "model": best.to_dict()}


@router.post("/models/classify")
async def classify_task(body: dict):
    """Classify a task description into a TaskType."""
    from jarvis.brain.model_router import router
    task_type = router.classify_task(body.get("description", ""))
    return {"task_type": task_type.value}


# ===== SPECULATIVE PLANNER =====

@router.get("/speculative/predictions")
async def get_predictions():
    """Get pending speculative predictions."""
    from jarvis.brain.speculative import speculative_planner
    pending = speculative_planner.get_pending()
    return {
        "predictions": [
            {
                "task_type": p.task_type,
                "description": p.description,
                "confidence": p.confidence,
                "suggested_worker": p.suggested_worker,
                "status": p.status,
            }
            for p in pending
        ],
        "total": len(pending),
    }


@router.get("/speculative/stats")
async def speculative_stats():
    """Get speculative planner stats."""
    from jarvis.brain.speculative import speculative_planner
    return speculative_planner.get_stats()


# ===== REVIEW PIPELINE =====

@router.get("/reviews/stats")
async def review_stats():
    """Get review pipeline statistics."""
    from jarvis.brain.review import review_pipeline
    return review_pipeline.get_stats()


@router.post("/reviews/review")
async def review_task(body: dict):
    """Manually review a task result."""
    from jarvis.brain.review import review_pipeline
    result = await review_pipeline.review(
        task_type=body.get("task_type", "unknown"),
        task_description=body.get("description", ""),
        result=body.get("result", ""),
        confidence=body.get("confidence", 0.5),
        issues=body.get("issues", []),
    )
    return result.to_dict()
