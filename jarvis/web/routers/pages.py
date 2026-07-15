"""Pages router - HTML templates."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

router = APIRouter(tags=["pages"])


@router.get("/")
async def index(request: Request):
    """Main JARVIS page."""
    return templates.TemplateResponse("index.html", {"request": request})


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
