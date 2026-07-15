"""Memory router - Preferences and data."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from jarvis.core.database import get_db

router = APIRouter(prefix="/api/memory", tags=["memory"])


class PreferenceRequest(BaseModel):
    key: str
    value: str


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
