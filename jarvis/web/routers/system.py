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


# ===== RAG MEMORY =====

@router.get("/rag/stats")
async def rag_stats():
    """Get RAG memory statistics."""
    from jarvis.brain.rag import rag_memory
    return rag_memory.get_stats()


@router.post("/rag/retrieve")
async def rag_retrieve(body: dict):
    """Retrieve relevant context for a query."""
    from jarvis.brain.rag import rag_memory, RAGQuery
    from jarvis.core.database import get_db
    db = await get_db()
    query = RAGQuery(
        text=body.get("text", ""),
        max_chunks=body.get("max_chunks", 10),
        min_relevance=body.get("min_relevance", 0.1),
        sources=body.get("sources", []),
    )
    chunks = await rag_memory.retrieve(query, db=db)
    return {
        "query": query.text,
        "chunks": [c.to_dict() for c in chunks],
        "total": len(chunks),
        "context": rag_memory.assemble_context(chunks),
    }


# ===== KNOWLEDGE GRAPH =====

@router.get("/graph/stats")
async def graph_stats():
    """Get knowledge graph statistics."""
    from jarvis.brain.memory.graph import KnowledgeGraph
    from jarvis.brain.graph_analysis import get_graph_analyzer
    graph = KnowledgeGraph()
    analyzer = get_graph_analyzer(graph)
    return await analyzer.get_stats()


@router.get("/graph/ego")
async def graph_ego(node_id: str, radius: int = 2):
    """Get ego graph (neighborhood) of a node."""
    from jarvis.brain.memory.graph import KnowledgeGraph
    from jarvis.brain.graph_analysis import get_graph_analyzer
    graph = KnowledgeGraph()
    analyzer = get_graph_analyzer(graph)
    return await analyzer.get_ego_graph(node_id, radius)


@router.get("/graph/path")
async def graph_path(source: str, target: str):
    """Find shortest path between two nodes."""
    from jarvis.brain.memory.graph import KnowledgeGraph
    from jarvis.brain.graph_analysis import get_graph_analyzer
    graph = KnowledgeGraph()
    analyzer = get_graph_analyzer(graph)
    path = await analyzer.shortest_path(source, target)
    return {"source": source, "target": target, "path": path, "found": path is not None}


@router.get("/graph/pagerank")
async def graph_pagerank():
    """Get PageRank importance scores."""
    from jarvis.brain.memory.graph import KnowledgeGraph
    from jarvis.brain.graph_analysis import get_graph_analyzer
    graph = KnowledgeGraph()
    analyzer = get_graph_analyzer(graph)
    scores = await analyzer.pagerank()
    # Return top 20
    top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:20]
    return {"scores": {k: round(v, 4) for k, v in top}, "total_nodes": len(scores)}


@router.post("/graph/extract")
async def graph_extract(body: dict):
    """Auto-extract entities and relations from text."""
    from jarvis.brain.memory.graph import KnowledgeGraph
    from jarvis.brain.graph_analysis import get_entity_extractor
    graph = KnowledgeGraph()
    extractor = get_entity_extractor()
    return await extractor.auto_extract(graph, body.get("text", ""))


@router.get("/graph/data")
async def graph_data(limit: int = 100):
    """Get graph nodes and edges for visualization."""
    from jarvis.brain.memory.graph import KnowledgeGraph
    graph = KnowledgeGraph()
    return await graph.get_graph_data(limit)


@router.post("/graph/node")
async def graph_add_node(body: dict):
    """Add a node to the knowledge graph."""
    from jarvis.brain.memory.graph import KnowledgeGraph, Node
    graph = KnowledgeGraph()
    node = Node(
        id=body["id"],
        label=body["label"],
        type=body.get("type", "concept"),
        content=body.get("content", ""),
    )
    return await graph.add_node(node)


@router.post("/graph/edge")
async def graph_add_edge(body: dict):
    """Add an edge to the knowledge graph."""
    from jarvis.brain.memory.graph import KnowledgeGraph, Edge
    graph = KnowledgeGraph()
    edge = Edge(
        source=body["source"],
        target=body["target"],
        relation=body.get("relation", "related_to"),
        weight=body.get("weight", 1.0),
    )
    return await graph.add_edge(edge)


# ===== SKILL EVOLUTION =====

@router.get("/evolution/stats")
async def evolution_stats():
    """Get skill evolution statistics."""
    from jarvis.brain.skill_evolution import skill_evolver
    return await skill_evolver.get_stats()


@router.get("/evolution/all")
async def evolution_all():
    """Get all skill evolutions."""
    from jarvis.brain.skill_evolution import skill_evolver
    return {"evolutions": await skill_evolver.get_all_evolutions()}


@router.get("/evolution/{skill_name}")
async def evolution_detail(skill_name: str):
    """Get evolution details for a specific skill."""
    from jarvis.brain.skill_evolution import skill_evolver
    evo = await skill_evolver.get_evolution(skill_name)
    if not evo:
        return {"error": "Skill not found"}
    return evo


@router.post("/evolution/variant")
async def evolution_add_variant(body: dict):
    """Add a strategy variant for A/B testing."""
    from jarvis.brain.skill_evolution import skill_evolver
    return await skill_evolver.add_variant(
        skill_name=body["skill_name"],
        variant_name=body["variant_name"],
        steps=body.get("steps", []),
    )


@router.post("/evolution/outcome")
async def evolution_record_outcome(body: dict):
    """Record an outcome for a skill variant."""
    from jarvis.brain.skill_evolution import skill_evolver
    await skill_evolver.record_outcome(
        skill_name=body["skill_name"],
        variant_name=body["variant_name"],
        success=body.get("success", True),
    )
    return {"ok": True}


@router.post("/evolution/compose")
async def evolution_compose(body: dict):
    """Compose multiple skills into a new one."""
    from jarvis.brain.skill_evolution import skill_evolver
    return await skill_evolver.compose_skills(
        skill_names=body["skill_names"],
        composed_name=body["composed_name"],
    )


@router.post("/evolution/prune")
async def evolution_prune():
    """Prune low-performing skill variants."""
    from jarvis.brain.skill_evolution import skill_evolver
    return await skill_evolver.prune_low_performers()
