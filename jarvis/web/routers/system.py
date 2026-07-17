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


# ===== ACI (Agent Communication Interface) =====

@router.get("/aci/stats")
async def aci_stats():
    """Get ACI statistics."""
    from jarvis.brain.aci import aci
    return aci.get_stats()


@router.get("/aci/history")
async def aci_history(
    sender: Optional[str] = None,
    receiver: Optional[str] = None,
    msg_type: Optional[str] = None,
    limit: int = 50,
):
    """Get ACI message history."""
    from jarvis.brain.aci import aci, MessageType
    mt = MessageType(msg_type) if msg_type else None
    msgs = aci.get_history(sender=sender, receiver=receiver, msg_type=mt, limit=limit)
    return {"messages": [m.to_dict() for m in msgs], "total": len(msgs)}


@router.get("/aci/queue/{agent_id}")
async def aci_peek(agent_id: str):
    """Peek at pending messages for an agent."""
    from jarvis.brain.aci import aci
    msgs = aci.peek(agent_id)
    return {"agent_id": agent_id, "pending": [m.to_dict() for m in msgs], "count": len(msgs)}


@router.post("/aci/send")
async def aci_send(body: dict):
    """Send a message via ACI."""
    from jarvis.brain.aci import aci, MessageType, MessagePriority
    msg = await aci.send(
        sender=body.get("sender", "J"),
        receiver=body.get("receiver", "♠K"),
        msg_type=MessageType(body.get("type", "query")),
        payload=body.get("payload", {}),
        priority=MessagePriority(body.get("priority", 1)),
    )
    return msg.to_dict()


@router.post("/aci/receive/{agent_id}")
async def aci_receive(agent_id: str):
    """Receive next message for an agent."""
    from jarvis.brain.aci import aci
    msg = await aci.receive(agent_id)
    if not msg:
        return {"empty": True}
    return msg.to_dict()


@router.post("/aci/broadcast")
async def aci_broadcast(body: dict):
    """Broadcast a message to all agents."""
    from jarvis.brain.aci import aci, MessageType, MessagePriority
    msg = await aci.send(
        sender=body.get("sender", "J"),
        receiver="*",
        msg_type=MessageType.BROADCAST,
        payload=body.get("payload", {}),
        priority=MessagePriority(body.get("priority", 1)),
    )
    return msg.to_dict()


# ===== DEMO LEARNING =====

@router.get("/demos")
async def list_demos(tag: Optional[str] = None):
    """List all recorded demos."""
    from jarvis.brain.demo_learning import demo_learner
    demos = await demo_learner.list_demos(tag=tag)
    return {"demos": [d.to_dict() for d in demos], "total": len(demos)}


@router.get("/demos/stats")
async def demo_stats():
    """Get demo learning statistics."""
    from jarvis.brain.demo_learning import demo_learner
    return demo_learner.get_stats()


@router.get("/demos/{demo_id}")
async def get_demo(demo_id: str):
    """Get a specific demo."""
    from jarvis.brain.demo_learning import demo_learner
    demo = await demo_learner.get_demo(demo_id)
    if not demo:
        return {"error": "Demo not found"}
    return demo.to_dict()


@router.post("/demos/start")
async def demo_start(body: dict):
    """Start recording a demo."""
    from jarvis.brain.demo_learning import demo_learner
    demo_id = await demo_learner.start_recording(
        name=body.get("name", "unnamed"),
        description=body.get("description", ""),
        tags=body.get("tags", []),
    )
    return {"demo_id": demo_id, "recording": True}


@router.post("/demos/action")
async def demo_action(body: dict):
    """Record an action during demo recording."""
    from jarvis.brain.demo_learning import demo_learner, Action
    action = Action(
        action_type=body.get("action_type", "click"),
        target=body.get("target", ""),
        value=body.get("value", ""),
        coordinates=tuple(body.get("coordinates", [0, 0])),
        duration_ms=body.get("duration_ms", 0),
        context=body.get("context", {}),
    )
    await demo_learner.record_action(action)
    return {"ok": True}


@router.post("/demos/stop")
async def demo_stop():
    """Stop recording and save the demo."""
    from jarvis.brain.demo_learning import demo_learner
    demo = await demo_learner.stop_recording()
    if not demo:
        return {"error": "No demo recording"}
    return demo.to_dict()


@router.post("/demos/{demo_id}/abstract")
async def demo_abstract(demo_id: str):
    """Abstract a demo into reusable patterns."""
    from jarvis.brain.demo_learning import demo_learner
    return await demo_learner.abstract_actions(demo_id)


@router.post("/demos/{demo_id}/replay")
async def demo_replay(demo_id: str, body: dict = None):
    """Replay a demo with optional variations."""
    from jarvis.brain.demo_learning import demo_learner
    variations = (body or {}).get("variations", {})
    return await demo_learner.replay(demo_id, variations)


@router.post("/demos/{demo_id}/outcome")
async def demo_outcome(demo_id: str, body: dict):
    """Record replay outcome."""
    from jarvis.brain.demo_learning import demo_learner
    await demo_learner.record_replay_outcome(demo_id, body.get("success", True))
    return {"ok": True}


# ===== DAG PLANNER =====

@router.get("/dag/missions")
async def dag_missions():
    """List all missions."""
    from jarvis.brain.dag_planner import dag_planner
    return {"missions": dag_planner.get_all_missions()}


@router.get("/dag/stats")
async def dag_stats():
    """Get DAG planner stats."""
    from jarvis.brain.dag_planner import dag_planner
    return dag_planner.get_stats()


@router.post("/dag/mission")
async def dag_create_mission(body: dict):
    """Create a new mission with task DAG."""
    from jarvis.brain.dag_planner import dag_planner, DAGNode
    nodes = [
        DAGNode(
            id=n["id"],
            name=n["name"],
            description=n.get("description", ""),
            assigned_to=n.get("assigned_to", ""),
            priority=n.get("priority", 5),
            dependencies=n.get("dependencies", []),
            estimated_duration_ms=n.get("estimated_duration_ms", 0),
        )
        for n in body.get("nodes", [])
    ]
    return dag_planner.create_mission(body.get("mission_id", f"mission_{int(time.time())}"), nodes)


@router.get("/dag/mission/{mission_id}")
async def dag_mission_status(mission_id: str):
    """Get mission status."""
    from jarvis.brain.dag_planner import dag_planner
    return dag_planner.get_mission_status(mission_id)


@router.get("/dag/mission/{mission_id}/next")
async def dag_next_tasks(mission_id: str):
    """Get next ready tasks."""
    from jarvis.brain.dag_planner import dag_planner
    return {"tasks": dag_planner.get_next_actions(mission_id)}


@router.post("/dag/mission/{mission_id}/start/{node_id}")
async def dag_start_task(mission_id: str, node_id: str):
    """Start a task."""
    from jarvis.brain.dag_planner import dag_planner
    node = dag_planner.start_task(mission_id, node_id)
    return {"ok": node is not None, "node": node.to_dict() if node else None}


@router.post("/dag/mission/{mission_id}/complete/{node_id}")
async def dag_complete_task(mission_id: str, node_id: str, body: dict = None):
    """Complete a task."""
    from jarvis.brain.dag_planner import dag_planner
    node = dag_planner.complete_task(mission_id, node_id, (body or {}).get("result", ""))
    return {"ok": node is not None, "node": node.to_dict() if node else None}


@router.get("/dag/mission/{mission_id}/visualize")
async def dag_visualize(mission_id: str):
    """Get DAG visualization data."""
    from jarvis.brain.dag_planner import dag_planner
    return dag_planner.visualize(mission_id)


# ===== DYNAMIC TEAMS =====

@router.get("/teams/stats")
async def team_stats():
    """Get team manager stats."""
    from jarvis.brain.teams import team_manager
    return team_manager.get_stats()


@router.post("/teams/form")
async def team_form(body: dict):
    """Form a dynamic team."""
    from jarvis.brain.teams import team_manager
    team = await team_manager.form_team(
        team_name=body.get("name", "unnamed"),
        mission_id=body.get("mission_id", ""),
        required_capabilities=body.get("capabilities", []),
        max_members=body.get("max_members", 5),
    )
    return team.to_dict()


@router.get("/teams/{team_id}")
async def team_detail(team_id: str):
    """Get team details."""
    from jarvis.brain.teams import team_manager
    team = await team_manager.get_team(team_id)
    return team.to_dict() if team else {"error": "Team not found"}


@router.post("/teams/{team_id}/disband")
async def team_disband(team_id: str):
    """Disband a team."""
    from jarvis.brain.teams import team_manager
    ok = await team_manager.disband_team(team_id)
    return {"ok": ok}


# ===== MISSION TIMELINE =====

@router.get("/timeline/{mission_id}")
async def timeline_get(mission_id: str, limit: int = 100):
    """Get mission timeline."""
    from jarvis.brain.teams import mission_timeline
    return {"timeline": mission_timeline.get_timeline(mission_id, limit)}


@router.get("/timeline/{mission_id}/visualize")
async def timeline_visualize(mission_id: str):
    """Get timeline visualization data."""
    from jarvis.brain.teams import mission_timeline
    return mission_timeline.visualize(mission_id)


@router.get("/timeline/{mission_id}/milestones")
async def timeline_milestones(mission_id: str):
    """Get mission milestones."""
    from jarvis.brain.teams import mission_timeline
    return {"milestones": mission_timeline.get_milestones(mission_id)}


@router.get("/timeline/{mission_id}/activity")
async def timeline_activity(mission_id: str):
    """Get per-agent activity."""
    from jarvis.brain.teams import mission_timeline
    return {"activity": mission_timeline.get_agent_activity(mission_id)}


@router.post("/timeline/{mission_id}/event")
async def timeline_record_event(mission_id: str, body: dict):
    """Record a timeline event."""
    from jarvis.brain.teams import mission_timeline
    mission_timeline.record_event(
        mission_id=mission_id,
        event_type=body.get("event_type", "milestone"),
        node_id=body.get("node_id", ""),
        node_name=body.get("node_name", ""),
        description=body.get("description", ""),
        agent_id=body.get("agent_id", ""),
    )
    return {"ok": True}
