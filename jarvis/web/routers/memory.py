"""Memory API endpoints.

Provides REST API for the human-like memory system:
- Working memory operations
- Episode CRUD
- Personal memory CRUD
- Journal entries
- Consolidation trigger
- Memory retrieval with context assembly
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ── Request/Response Models ──────────────────────────────────

class WorkingMemoryUpdate(BaseModel):
    slot: str = Field(..., description="working|conversation|mission|project|agents|files|decisions|user_context")
    content: str
    importance: float = Field(0.5, ge=0, le=1)
    ttl_seconds: Optional[int] = Field(None, ge=0)
    metadata: dict = Field(default_factory=dict)

class EpisodeCreate(BaseModel):
    title: str
    summary: str = ""
    episode_type: str = Field("conversation", pattern="^(conversation|decision|milestone|learning|bug|meeting|mission)$")
    participants: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    importance_score: int = Field(50, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)

class PersonalMemoryCreate(BaseModel):
    category: str = Field(..., pattern="^(preference|rule|goal|habit|fact|relationship|project_context|tool_usage|learning)$")
    key: str
    value: str
    confidence: float = Field(0.6, ge=0, le=1)
    remember_mode: str = Field("always_remember", pattern="^(always_remember|ask_before|never_remember)$")

class JournalUpdate(BaseModel):
    summary: Optional[str] = None
    highlights: Optional[list[str]] = None
    decisions: Optional[list[str]] = None
    tomorrow: Optional[list[str]] = None
    mood: Optional[str] = Field(None, pattern="^(neutral|focused|productive|stuck)$")
    tags: Optional[list[str]] = None

class RetrievalQuery(BaseModel):
    query: str
    max_results: int = Field(10, ge=1, le=50)
    memory_types: Optional[list[str]] = None

class ConsolidateRequest(BaseModel):
    force: bool = False


# ── Working Memory ───────────────────────────────────────────

@router.get("/working")
async def get_working_memory():
    from ...brain.memory.working import get_working_memory
    wm = get_working_memory()
    entries = await wm.get_all()
    context = await wm.get_context()
    return {
        "slots": {k: {
            "content": v.get("content", "")[:200],
            "importance": v.get("importance", 0),
            "created_at": v.get("created_at"),
        } for k, v in entries.items()},
        "context_summary": context[:500],
    }


@router.post("/working")
async def update_working_memory(req: WorkingMemoryUpdate):
    from ...brain.memory.working import get_working_memory
    wm = get_working_memory()
    await wm.update(
        req.slot, req.content,
        importance=req.importance,
        ttl_seconds=req.ttl_seconds,
        metadata=req.metadata,
    )
    return {"status": "updated", "slot": req.slot}


# ── Episodes ─────────────────────────────────────────────────

@router.get("/episodes")
async def list_episodes(limit: int = 20, episode_type: Optional[str] = None):
    from ...brain.memory.episodic import get_episodic_memory
    em = get_episodic_memory()
    if episode_type:
        # Filter by type via search
        episodes = await em.search(episode_type, limit=limit)
        episodes = [ep for ep in episodes if ep.episode_type == episode_type]
    else:
        episodes = await em.get_recent(limit=limit)
    return {"episodes": [ep.to_dict() for ep in episodes]}


@router.post("/episodes")
async def create_episode(req: EpisodeCreate):
    from ...brain.memory.episodic import get_episodic_memory
    em = get_episodic_memory()
    result = await em.create_episode(
        title=req.title,
        summary=req.summary,
        episode_type=req.episode_type,
        participants=req.participants,
        decisions=req.decisions,
        importance_score=req.importance_score,
        tags=req.tags,
    )
    return result


@router.get("/episodes/{episode_id}")
async def get_episode(episode_id: int):
    from ...brain.memory.episodic import get_episodic_memory
    em = get_episodic_memory()
    ep = await em.get(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep.to_dict()


@router.get("/episodes/timeline")
async def episode_timeline(days: int = 30):
    from ...brain.memory.episodic import get_episodic_memory
    em = get_episodic_memory()
    timeline = await em.get_timeline(days=days)
    return {"timeline": timeline}


# ── Personal Memory ──────────────────────────────────────────

@router.get("/personal")
async def list_personal_memory(category: Optional[str] = None):
    from ...brain.memory.personal import get_personal_memory
    pm = get_personal_memory()
    if category:
        memories = await pm.get_by_category(category)
    else:
        categories = ["preference", "rule", "goal", "habit", "fact", "project_context", "tool_usage"]
        memories = []
        for cat in categories:
            memories.extend(await pm.get_by_category(cat))
    return {"memories": [m.to_dict() for m in memories]}


@router.post("/personal")
async def create_personal_memory(req: PersonalMemoryCreate):
    from ...brain.memory.personal import get_personal_memory
    pm = get_personal_memory()
    result = await pm.remember(
        req.category, req.key, req.value,
        confidence=req.confidence,
        remember_mode=req.remember_mode,
    )
    return result


@router.get("/personal/profile")
async def get_profile():
    from ...brain.memory.personal import get_personal_memory
    pm = get_personal_memory()
    profile = await pm.get_profile()
    return {"profile": profile}


@router.delete("/personal/{category}/{key}")
async def forget_personal_memory(category: str, key: str):
    from ...brain.memory.personal import get_personal_memory
    pm = get_personal_memory()
    result = await pm.forget(category=category, key=key)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"status": "forgotten", "category": category, "key": key}


# ── Journal ──────────────────────────────────────────────────

@router.get("/journal")
async def get_journal_entries(days: int = 7):
    from ...brain.memory.journal import get_journal
    j = get_journal()
    entries = await j.get_recent(days)
    return {"entries": [e.__dict__ for e in entries]}


@router.get("/journal/today")
async def get_today_journal():
    from ...brain.memory.journal import get_journal
    j = get_journal()
    entry = await j.get_today()
    return entry.__dict__ if entry else {"date": j._today(), "empty": True}


@router.put("/journal")
async def update_journal(req: JournalUpdate):
    from ...brain.memory.journal import get_journal
    j = get_journal()
    if req.summary:
        await j.set_summary(req.summary)
    if req.highlights:
        for h in req.highlights:
            await j.add_highlight(h)
    if req.decisions:
        for d in req.decisions:
            await j.add_decision(d)
    if req.tomorrow:
        await j.set_tomorrow(req.tomorrow)
    if req.mood:
        await j.set_mood(req.mood)
    return {"status": "updated"}


# ── Retrieval ────────────────────────────────────────────────

@router.post("/retrieve")
async def retrieve_memories(req: RetrievalQuery):
    from ...brain.memory.retrieval import get_retrieval_engine
    engine = get_retrieval_engine()
    results = await engine.retrieve(
        req.query,
        max_results=req.max_results,
        memory_types=req.memory_types,
    )
    context = engine.assemble_context(results)
    return {
        "results": [r.to_dict() for r in results],
        "context": context,
        "stats": engine.get_stats(),
    }


# ── Consolidation ────────────────────────────────────────────

@router.post("/consolidate")
async def trigger_consolidation(req: ConsolidateRequest):
    from ...brain.memory.consolidation import get_consolidator
    c = get_consolidator()
    result = await c.consolidate(force=req.force)
    return result


# ── Importance Scoring ───────────────────────────────────────

@router.post("/score")
async def score_importance(body: dict):
    from ...brain.memory.importance import importance_scorer
    score = importance_scorer.score(
        body.get("content", ""),
        context=body.get("context", {}),
    )
    signals = importance_scorer.extract_signals(body.get("content", ""))
    return {"score": score, "signals": signals}
