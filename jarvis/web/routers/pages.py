"""Pages router — HTML templates (v8.0.0)."""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

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
    return templates.TemplateResponse(request, "base.html")


@router.get("/history")
async def history_page(request: Request):
    """History page — redirects to main app chat history."""
    return templates.TemplateResponse(request, "base.html")


@router.get("/dashboard")
async def developer_dashboard(request: Request):
    """Developer Dashboard — live system health."""
    return templates.TemplateResponse(request, "developer_dashboard.html")


@router.get("/core")
async def core_page(request: Request):
    """Fullscreen golden core — desktop app surface."""
    return templates.TemplateResponse(request, "core.html")
