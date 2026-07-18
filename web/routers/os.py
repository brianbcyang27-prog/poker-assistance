"""OS Integration API — REST endpoints for system-level control."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

router = APIRouter(prefix="/api/os", tags=["os"])


class NotifyRequest(BaseModel):
    title: str
    message: str
    subtitle: Optional[str] = None
    sound: bool = True


class ClipboardWriteRequest(BaseModel):
    text: str


class HotkeyRegisterRequest(BaseModel):
    shortcut: str
    action: str
    description: str = ""


class WatchRequest(BaseModel):
    path: str
    key: Optional[str] = None
    recursive: bool = True


@router.get("/status")
async def get_os_status():
    """Get OS integration status."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    await os_mgr.initialize()
    return {"ok": True, **os_mgr.get_status()}


@router.get("/info")
async def get_system_info():
    """Get system information."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    await os_mgr.initialize()
    info = await os_mgr.get_system_info()
    return {"ok": True, **info}


# ── Notifications ────────────────────────────────────────

@router.post("/notify")
async def send_notification(req: NotifyRequest):
    """Send a system notification."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    await os_mgr.initialize()
    ok = await os_mgr.notify(req.title, req.message, req.subtitle, req.sound)
    return {"ok": ok}


@router.get("/notifications")
async def get_notification_history():
    """Get recent notification history."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    return {"ok": True, "notifications": os_mgr.notifications.get_history()}


# ── Clipboard ────────────────────────────────────────────

@router.get("/clipboard")
async def read_clipboard():
    """Read clipboard content."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    await os_mgr.initialize()
    content = await os_mgr.clipboard_read()
    return {"ok": True, "content": content, "has_content": content is not None and len(content) > 0}


@router.post("/clipboard")
async def write_clipboard(req: ClipboardWriteRequest):
    """Write to clipboard."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    await os_mgr.initialize()
    ok = await os_mgr.clipboard_write(req.text)
    return {"ok": ok, "length": len(req.text)}


@router.delete("/clipboard")
async def clear_clipboard():
    """Clear clipboard."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    await os_mgr.initialize()
    ok = await os_mgr.clipboard_clear()
    return {"ok": ok}


@router.get("/clipboard/history")
async def get_clipboard_history():
    """Get clipboard history."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    return {"ok": True, "history": os_mgr.clipboard_history()}


# ── Hotkeys ──────────────────────────────────────────────

@router.get("/hotkeys")
async def list_hotkeys():
    """List registered hotkeys."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    return {"ok": True, "hotkeys": os_mgr.hotkey_list()}


@router.post("/hotkeys")
async def register_hotkey(req: HotkeyRegisterRequest):
    """Register a hotkey."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    ok = os_mgr.hotkey_register(req.shortcut, req.action, req.description)
    return {"ok": ok}


@router.delete("/hotkeys/{action}")
async def unregister_hotkey(action: str):
    """Unregister a hotkey."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    ok = os_mgr.hotkey_unregister(action)
    return {"ok": ok}


# ── Menu Bar ─────────────────────────────────────────────

@router.get("/menubar")
async def list_menubar_items():
    """List menu bar items."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    return {"ok": True, "items": os_mgr.menubar_list()}


# ── File Watcher ─────────────────────────────────────────

@router.get("/watcher")
async def list_watched_directories():
    """List watched directories."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    return {"ok": True, "directories": os_mgr.watched_directories()}


@router.post("/watcher")
async def watch_directory(req: WatchRequest):
    """Watch a directory."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    await os_mgr.initialize()
    ok = await os_mgr.watch_directory(req.path, req.key, req.recursive)
    return {"ok": ok, "path": req.path}


@router.delete("/watcher/{key}")
async def unwatch_directory(key: str):
    """Stop watching a directory."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    ok = await os_mgr.unwatch_directory(key)
    return {"ok": ok}


@router.get("/watcher/events")
async def get_file_events():
    """Get recent file events."""
    from jarvis.os import get_os_manager
    os_mgr = get_os_manager()
    return {"ok": True, "events": os_mgr.file_events()}
