"""Computer use API endpoints."""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from jarvis.web.rate_limit import rate_limit

router = APIRouter(prefix="/api/computer", tags=["computer"])


class ActionRequest(BaseModel):
    action: str
    params: Optional[dict] = {}


@router.post("/action")
@rate_limit(max_requests=5, window_seconds=30)
async def execute_action(request: Request, req: ActionRequest):
    """Execute a computer action with permission check."""
    from jarvis.computer.controller import controller
    from jarvis.core.permissions import permission_center
    
    # Map actions to required permissions
    action_permissions = {
        "screen_capture": ["screen"],
        "screen_capture_region": ["screen"],
        "screen_get_active_window": ["screen"],
        "screen_list_windows": ["screen"],
        "shell_execute": ["terminal"],
        "browser_navigate": ["browser"],
        "browser_screenshot": ["browser"],
        "browser_click": ["browser"],
        "browser_type": ["browser"],
        "browser_get_text": ["browser"],
        "browser_scroll": ["browser"],
        "list_files": ["files"],
        "read_file": ["files"],
        "write_file": ["files"],
        "create_file": ["files"],
    }
    
    # Check permissions
    required = action_permissions.get(req.action, [])
    if required:
        all_granted, missing = permission_center.check_required(required)
        if not all_granted:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {', '.join(missing)} required for {req.action}"
            )
    
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
        {"name": "list_files", "params": ["path"], "description": "List files in a directory"},
        {"name": "read_file", "params": ["path"], "description": "Read file contents"},
        {"name": "write_file", "params": ["path", "content"], "description": "Write content to a file"},
        {"name": "create_file", "params": ["path", "content"], "description": "Create a new file"},
        {"name": "file_exists", "params": ["path"], "description": "Check if file exists"},
        {"name": "shell_execute", "params": ["command"], "description": "Execute shell command"},
    ]}


@router.post("/shutdown")
async def shutdown():
    from jarvis.computer.controller import controller
    await controller.shutdown()
    return {"ok": True}


class WorkflowRequest(BaseModel):
    workflow: str
    params: Optional[dict] = {}


@router.post("/workflow")
@rate_limit(max_requests=3, window_seconds=60)
async def execute_workflow(request: Request, req: WorkflowRequest):
    """Execute a predefined workflow."""
    from jarvis.core.workflows import workflows
    
    if req.workflow not in workflows.list_workflows():
        raise HTTPException(status_code=400, detail=f"Unknown workflow: {req.workflow}")
    
    result = await workflows.execute(req.workflow, **req.params)
    return result.to_dict()


@router.get("/workflows")
async def list_workflows():
    """List available workflows."""
    from jarvis.core.workflows import workflows
    return {"workflows": workflows.list_workflows()}
