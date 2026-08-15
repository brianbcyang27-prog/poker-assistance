"""Know-Me profile API.

GET    /api/profile                → profile dict {category: {key: {value, confidence}}}
GET    /api/profile/completeness   → {score, completeness, percent, ...}
POST   /api/profile/learn          → store one memory {content, category, source}
POST   /api/profile/onboard        → store onboarding memories {name, timezone, goal, notes}
"""

from __future__ import annotations

import re
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...brain.memory.personal import get_personal_memory

router = APIRouter(prefix="/api/profile", tags=["profile"])

CATEGORY_LABELS = {
    "bio": "Who you are",
    "preference": "Preferences",
    "style": "Style",
    "workflow": "Workflow",
    "tool": "Tools",
    "project": "Projects",
    "context": "Context",
    "goal": "Goals",
    "rule": "Rules",
}


class LearnRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    category: str = Field(
        "context",
        pattern="^(bio|preference|style|workflow|tool|project|context|goal|rule)$",
    )
    source: str = Field("ui", max_length=100)


class OnboardRequest(BaseModel):
    name: str = Field("", max_length=200)
    timezone: str = Field("", max_length=100)
    goal: str = Field("", max_length=1000)
    notes: str = Field("", max_length=2000)


def _slugify(content: str) -> str:
    parts = re.split(r"[\s,.:;!?]+", content.strip())
    return "_".join([p for p in parts if p]).lower()[:80] or "note"


@router.get("")
async def get_profile() -> dict:
    pm = get_personal_memory()
    return await pm.get_profile()


@router.get("/completeness")
async def get_completeness() -> dict:
    pm = get_personal_memory()
    memories = await pm.get_all()
    by_cat: dict[str, set[str]] = {}
    for m in memories:
        by_cat.setdefault(m.category, set()).add(m.key)

    score = 0
    breakdown: dict[str, dict] = {}
    checks = [
        ("bio", 25, lambda keys: "my_name" in keys or bool(keys)),
        ("preference", 10, lambda keys: "timezone" in keys or bool(keys)),
        ("goal", 20, bool),
        ("project", 15, bool),
        ("tool", 10, bool),
        ("style", 5, bool),
        ("workflow", 5, bool),
        ("rule", 5, bool),
        ("context", 5, bool),
    ]
    for category, points, check in checks:
        keys = by_cat.get(category, set())
        met = bool(check(keys))
        if met:
            score += points
        breakdown[category] = {
            "label": CATEGORY_LABELS.get(category, category),
            "points": points,
            "met": met,
        }

    return {
        "score": score,
        "completeness": score,
        "percent": score,
        "total_memories": len(memories),
        "breakdown": breakdown,
    }


@router.post("/learn")
async def learn(req: LearnRequest) -> dict:
    pm = get_personal_memory()
    result = await pm.remember(
        category=req.category,
        key=_slugify(req.content),
        value=req.content,
        confidence=0.9,
        source=req.source or "ui",
    )
    return {"ok": True, **result, "category": req.category, "key": _slugify(req.content)}


@router.post("/onboard")
async def onboard(req: OnboardRequest) -> dict:
    pm = get_personal_memory()
    now = time.time()
    saved = 0
    if req.name:
        await pm.remember(
            "bio", "my_name", f"My name is {req.name}",
            confidence=0.95, source="onboarding",
        )
        saved += 1
    if req.timezone:
        await pm.remember(
            "preference", "timezone", f"My timezone is {req.timezone}",
            confidence=0.9, source="onboarding",
        )
        saved += 1
    if req.goal:
        await pm.remember(
            "goal", "current_goal", f"Currently building: {req.goal}",
            confidence=0.9, source="onboarding",
        )
        saved += 1
    if req.notes:
        await pm.remember(
            "context", _slugify(req.notes) or "about_me", req.notes,
            confidence=0.8, source="onboarding",
        )
        saved += 1
    return {"ok": True, "memories_saved": saved, "completed_at": now}
