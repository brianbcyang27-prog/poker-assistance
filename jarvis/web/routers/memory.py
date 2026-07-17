"""Memory router - Preferences, data, knowledge graph, and notes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from jarvis.core.database import get_db

router = APIRouter(prefix="/api/memory", tags=["memory"])


class PreferenceRequest(BaseModel):
    key: str
    value: str


class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = []


class NoteUpdate(BaseModel):
    content: str


class ExtractRequest(BaseModel):
    text: str
    agent_id: str = "jarvis"


class GraphNodeRequest(BaseModel):
    id: str
    label: str
    type: str = "concept"
    content: str = ""


class GraphEdgeRequest(BaseModel):
    source: str
    target: str
    relation: str = "related_to"
    weight: float = 1.0


# Original endpoints

@router.get("")
async def get_memory():
    """Get all memory data."""
    db = await get_db()
    preferences = await db.get_all_preferences()
    projects = await db.get_all_projects()
    decisions = await db.get_decisions()
    return {
        "preferences": preferences,
        "projects": projects,
        "decisions": decisions,
    }


@router.get("/preferences")
async def get_preferences():
    """Get all preferences."""
    db = await get_db()
    return await db.get_all_preferences()


@router.post("/preferences")
async def set_preference(req: PreferenceRequest):
    """Set a preference."""
    db = await get_db()
    await db.set_preference(req.key, req.value)
    return {"status": "ok"}


@router.get("/projects")
async def get_projects():
    """Get all projects."""
    db = await get_db()
    return await db.get_all_projects()


@router.get("/decisions")
async def get_decisions():
    """Get important decisions."""
    db = await get_db()
    return await db.get_decisions()


# Notes endpoints (Obsidian-style)

@router.post("/notes")
async def create_note(req: NoteCreate):
    from jarvis.brain.memory.note import notes
    return await notes.create_note(req.title, req.content, req.tags)


@router.get("/notes")
async def list_notes(limit: int = 50):
    from jarvis.brain.memory.note import notes
    return await notes.list_notes(limit)


@router.get("/notes/{note_id}")
async def get_note(note_id: str):
    from jarvis.brain.memory.note import notes
    result = await notes.get_note(note_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail="Note not found")
    return result


@router.put("/notes/{note_id}")
async def update_note(note_id: str, req: NoteUpdate):
    from jarvis.brain.memory.note import notes
    return await notes.update_note(note_id, req.content)


@router.delete("/notes/{note_id}")
async def delete_note(note_id: str):
    from jarvis.brain.memory.note import notes
    return await notes.delete_note(note_id)


@router.get("/notes/search/{query}")
async def search_notes(query: str, limit: int = 20):
    from jarvis.brain.memory.note import notes
    return await notes.search_notes(query, limit)


@router.get("/backlinks/{note_id}")
async def get_backlinks(note_id: str):
    from jarvis.brain.memory.note import notes
    backlinks = await notes._get_backlinks(note_id)
    return {"ok": True, "backlinks": backlinks}


# Knowledge graph endpoints

@router.get("/graph")
async def get_graph(limit: int = 200):
    from jarvis.brain.memory.graph import graph
    return await graph.get_graph_data(limit)


@router.get("/graph/stats")
async def get_graph_stats():
    from jarvis.brain.memory.graph import graph
    return await graph.get_stats()


@router.get("/graph/node/{node_id}")
async def get_node(node_id: str):
    from jarvis.brain.memory.graph import graph
    node = await graph.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    neighbors = await graph.get_neighbors(node_id)
    return {"ok": True, "node": node, "neighbors": neighbors}


@router.post("/graph/node")
async def add_node(req: GraphNodeRequest):
    from jarvis.brain.memory.graph import graph, Node
    node = Node(id=req.id, label=req.label, type=req.type, content=req.content)
    return await graph.add_node(node)


@router.post("/graph/edge")
async def add_edge(req: GraphEdgeRequest):
    from jarvis.brain.memory.graph import graph, Edge
    edge = Edge(source=req.source, target=req.target, relation=req.relation, weight=req.weight)
    return await graph.add_edge(edge)


@router.get("/graph/search/{query}")
async def search_graph(query: str, type: Optional[str] = None, limit: int = 20):
    from jarvis.brain.memory.graph import graph
    return await graph.search_nodes(query, type, limit)


# Knowledge extraction

@router.post("/extract")
async def extract_knowledge(req: ExtractRequest):
    from jarvis.brain.memory.extractor import knowledge_extractor
    return await knowledge_extractor.process_message("user", req.text, req.agent_id)


# ── Project Memory Endpoints ────────────────────────────────────────

class ProjectRegisterRequest(BaseModel):
    name: str
    path: str
    description: str = ""
    language: str = ""
    server_command: str = ""
    server_port: int = 0
    url: str = ""
    ai_tool_command: str = ""
    ai_tool_name: str = ""
    context: dict = {}


@router.get("/projects/all")
async def list_all_projects(status: Optional[str] = None):
    """List all registered projects with full metadata."""
    from jarvis.brain.project_memory import project_memory
    return await project_memory.list_projects(status=status)


@router.get("/projects/active")
async def get_active_project():
    """Get the most recently active project."""
    from jarvis.brain.project_memory import project_memory
    project = await project_memory.get_active_project()
    if not project:
        return {"error": "No active project"}
    return project


@router.post("/projects/register")
async def register_project(req: ProjectRegisterRequest):
    """Register a new project."""
    from jarvis.brain.project_memory import project_memory
    return await project_memory.register_project(
        name=req.name,
        path=req.path,
        description=req.description,
        language=req.language,
        server_command=req.server_command,
        server_port=req.server_port,
        url=req.url,
        ai_tool_command=req.ai_tool_command,
        ai_tool_name=req.ai_tool_name,
        context=req.context,
    )


@router.post("/projects/{name}/touch")
async def touch_project(name: str):
    """Update last_worked_on timestamp for a project."""
    from jarvis.brain.project_memory import project_memory
    await project_memory.record_activity(name)
    return {"ok": True}


@router.post("/projects/{name}/resume")
async def resume_project(name: str):
    """Resume a project — launch server, browser, AI tool."""
    from jarvis.computer.controller import controller
    return await controller.execute("resume_project", name=name)


@router.delete("/projects/{name}")
async def delete_project(name: str):
    """Delete a project."""
    from jarvis.brain.project_memory import project_memory
    deleted = await project_memory.delete_project(name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}
