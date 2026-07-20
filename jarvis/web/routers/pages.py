"""Pages router — HTML templates (v6.1.0)."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pathlib import Path

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

router = APIRouter(tags=["pages"])


@router.get("/api/health")
async def health_check():
    """Simple health check endpoint."""
    from jarvis import __version__
    return JSONResponse({"status": "ok", "version": __version__, "service": "jarvis"})


@router.get("/")
async def index(request: Request):
    """Main JARVIS page — the living interface."""
    return templates.TemplateResponse("base.html", {"request": request})


@router.get("/command-map")
async def command_map(request: Request):
    """Agent Command Map page."""
    return templates.TemplateResponse("command-map.html", {"request": request})


@router.get("/settings")
async def settings_page(request: Request):
    """Settings page."""
    return templates.TemplateResponse("settings.html", {"request": request})


@router.get("/history")
async def history_page(request: Request):
    """Task History page."""
    return templates.TemplateResponse("history.html", {"request": request})


@router.get("/dashboard")
async def developer_dashboard(request: Request):
    """Developer Dashboard — live system health."""
    return templates.TemplateResponse("developer_dashboard.html", {"request": request})
