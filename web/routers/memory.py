from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_db

router = APIRouter(prefix="/api", tags=["memory"])


class PreferenceRequest(BaseModel):
    key: str
    value: str


class ProjectRequest(BaseModel):
    name: str
    path: str
    language: str = "unknown"


@router.get("/memory")
async def get_memory():
    db = await get_db()

    prefs_cursor = await db.execute("SELECT key, value FROM preferences")
    prefs = {r["key"]: r["value"] for r in await prefs_cursor.fetchall()}

    projects_cursor = await db.execute("SELECT id, name, path, language, created_at FROM projects")
    projects = [dict(r) for r in await projects_cursor.fetchall()]

    history_cursor = await db.execute(
        "SELECT plan_id, user_request, summary, created_at FROM task_history ORDER BY id DESC LIMIT 10"
    )
    history = [dict(r) for r in await history_cursor.fetchall()]

    return {"preferences": prefs, "projects": projects, "recent_tasks": history}


@router.post("/memory")
async def set_preference(req: PreferenceRequest):
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)",
        (req.key, req.value),
    )
    await db.commit()
    return {"stored": True, "key": req.key, "value": req.value}


@router.delete("/memory/{key}")
async def delete_preference(key: str):
    db = await get_db()
    await db.execute("DELETE FROM preferences WHERE key = ?", (key,))
    await db.commit()
    return {"deleted": True}


@router.get("/projects")
async def list_projects():
    db = await get_db()
    cursor = await db.execute("SELECT id, name, path, language, created_at FROM projects")
    return [dict(r) for r in await cursor.fetchall()]


@router.post("/projects")
async def add_project(req: ProjectRequest):
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO projects (name, path, language) VALUES (?, ?, ?)",
            (req.name, req.path, req.language),
        )
        await db.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Project already exists")
    return {"added": True, "name": req.name}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    db = await get_db()
    await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    await db.commit()
    return {"deleted": True}


@router.get("/sessions")
async def list_sessions():
    db = await get_db()
    cursor = await db.execute("""
        SELECT session_id, MIN(timestamp) as started, MAX(timestamp) as last_message,
               COUNT(*) as message_count
        FROM conversations
        GROUP BY session_id
        ORDER BY last_message DESC
        LIMIT 20
    """)
    return [dict(r) for r in await cursor.fetchall()]
