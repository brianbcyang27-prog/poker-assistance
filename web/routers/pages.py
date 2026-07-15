from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from config import BASE_DIR

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
