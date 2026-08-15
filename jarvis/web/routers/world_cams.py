"""Webcam monitor router — world sources, status, events, scan and test alerts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.world import sources
from jarvis.world.monitor import world_monitor
from jarvis.world.notify import send_imessage, send_telegram

router = APIRouter(prefix="/api/world", tags=["world"])


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = "live"
    location: str = ""
    image_url: str


class SourceUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    location: str | None = None
    image_url: str | None = None
    enabled: bool | None = None
    thresholds: dict | None = None


def _validate_image_url(image_url: str) -> None:
    if not image_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="image_url must start with http:// or https://")


@router.get("/sources")
async def get_sources():
    return {"sources": sources.list_sources()}


@router.post("/sources")
async def create_source(payload: SourceCreate):
    _validate_image_url(payload.image_url)
    source = sources.add_source(
        name=payload.name,
        kind=payload.kind,
        location=payload.location,
        image_url=payload.image_url,
    )
    if source is None:
        raise HTTPException(status_code=400, detail="Could not add source (invalid or at cap)")
    return {"source": source}


@router.patch("/sources/{source_id}")
async def patch_source(source_id: str, payload: SourceUpdate):
    changes = payload.model_dump(exclude_none=True)
    if "image_url" in changes:
        _validate_image_url(changes["image_url"])
    source = sources.update_source(source_id, **changes)
    if source is None:
        raise HTTPException(status_code=404, detail="Unknown source")
    return {"source": source}


@router.delete("/sources/{source_id}")
async def delete_source(source_id: str):
    if not sources.remove_source(source_id):
        raise HTTPException(status_code=404, detail="Unknown source")
    return {"ok": True}


@router.get("/status")
async def get_status():
    return await world_monitor.status()


@router.get("/events")
async def get_events(limit: int = 50):
    return {"events": sources.recent_events(limit)}


@router.post("/scan")
async def scan_now():
    return await world_monitor.scan_once()


@router.post("/notify/test")
async def notify_test():
    config = sources.get_config()
    telegram = await send_telegram("JARVIS — World Monitor test alert")
    imessage = await send_imessage(
        config.get("imessage_target"), "JARVIS — World Monitor test alert"
    )
    return {"ok": telegram or imessage, "channels": {"telegram": telegram, "imessage": imessage}}
