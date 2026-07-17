"""Computer use API endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/api/computer", tags=["computer"])


class ActionRequest(BaseModel):
    action: str
    params: Optional[dict] = {}


@router.post("/action")
async def execute_action(req: ActionRequest):
    from jarvis.computer.controller import controller
    result = await controller.execute(req.action, **req.params)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "Action failed"))
    return result


@router.get("/actions")
async def list_actions():
    return {"actions": [
        {"name": "browser_navigate", "params": ["url"], "description": "Navigate to a URL"},
        {"name": "browser_screenshot", "params": [], "description": "Screenshot current page"},
        {"name": "browser_get_text", "params": [], "description": "Get page text content"},
        {"name": "browser_click", "params": ["selector"], "description": "Click an element"},
        {"name": "browser_type", "params": ["selector", "text"], "description": "Type into an input"},
        {"name": "browser_scroll", "params": ["direction"], "description": "Scroll the page"},
        {"name": "web_search", "params": ["query"], "description": "Search the web"},
        {"name": "web_fetch", "params": ["url"], "description": "Fetch and extract text from URL"},
        {"name": "screen_capture", "params": [], "description": "Capture the screen"},
        {"name": "screen_get_active_window", "params": [], "description": "Get active window info"},
        {"name": "screen_list_windows", "params": [], "description": "List all windows"},
        {"name": "open_app", "params": ["app_name"], "description": "Open an application"},
        {"name": "open_url", "params": ["url"], "description": "Open URL in default browser"},
        {"name": "type_text", "params": ["text"], "description": "Type text via keyboard"},
        {"name": "hotkey", "params": ["keys"], "description": "Press keyboard shortcut"},
        {"name": "press_key", "params": ["key"], "description": "Press a single key"},
    ]}


@router.post("/shutdown")
async def shutdown():
    from jarvis.computer.controller import controller
    await controller.shutdown()
    return {"ok": True}
