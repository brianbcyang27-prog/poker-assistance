"""JARVIS Web - FastAPI Application."""

import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jarvis.core.config import get_config
from jarvis.core.database import get_db
from jarvis.agents.jarvis import JarvisAgent
from jarvis.agents.kings import EngineeringKing, PersonalKing, ResearchKing, SystemKing
from jarvis.agents.workers import (
    ArchitectWorker, BackendWorker, FrontendWorker,
    ReactWorker, PythonWorker, TestingWorker, DocsWorker, A11yWorker,
    CalendarWorker, EmailWorker, TasksWorker, SchedulingWorker,
    WebResearchWorker, DocumentationWorker, FactCheckWorker,
    FilesWorker, TerminalWorker, ApplicationsWorker,
)
from jarvis.workspace.manager import WorkspaceManager

# Global agent instances
jarvis: JarvisAgent = None
workspace_manager: WorkspaceManager = None


def initialize_agents() -> JarvisAgent:
    """Initialize the JARVIS agent hierarchy."""
    global jarvis
    
    # Create JARVIS
    jarvis = JarvisAgent()
    
    # Create Kings
    eng_king = EngineeringKing()
    personal_king = PersonalKing()
    research_king = ResearchKing()
    system_king = SystemKing()
    
    # Register Kings with JARVIS
    jarvis.register_king(eng_king)
    jarvis.register_king(personal_king)
    jarvis.register_king(research_king)
    jarvis.register_king(system_king)
    
    # Create and register Engineering workers
    eng_king.register_worker(ArchitectWorker())
    eng_king.register_worker(BackendWorker())
    eng_king.register_worker(FrontendWorker())
    eng_king.register_worker(ReactWorker())
    eng_king.register_worker(PythonWorker())
    eng_king.register_worker(TestingWorker())
    eng_king.register_worker(DocsWorker())
    eng_king.register_worker(A11yWorker())
    
    # Create and register Personal workers
    personal_king.register_worker(CalendarWorker())
    personal_king.register_worker(EmailWorker())
    personal_king.register_worker(TasksWorker())
    personal_king.register_worker(SchedulingWorker())
    
    # Create and register Research workers
    research_king.register_worker(WebResearchWorker())
    research_king.register_worker(DocumentationWorker())
    research_king.register_worker(FactCheckWorker())
    
    # Create and register System workers
    system_king.register_worker(FilesWorker())
    system_king.register_worker(TerminalWorker())
    system_king.register_worker(ApplicationsWorker())
    
    return jarvis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    config = get_config()
    
    # Initialize database
    db = await get_db()
    
    # Initialize agents
    initialize_agents()
    
    # Initialize workspace manager
    global workspace_manager
    workspace_manager = WorkspaceManager()
    
    yield
    
    # Shutdown
    await db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="JARVIS",
        description="Multi-Agent AI Operating System",
        version="2.0.0",
        lifespan=lifespan,
    )
    
    # Mount static files
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Include routers
    from .routers import chat, agents, workspace, memory, voice, pages, websocket, settings
    app.include_router(chat.router)
    app.include_router(agents.router)
    app.include_router(workspace.router)
    app.include_router(memory.router)
    app.include_router(voice.router)
    app.include_router(pages.router)
    app.include_router(websocket.router)
    app.include_router(settings.router)
    
    return app


def run():
    """Run the JARVIS web server."""
    config = get_config()
    app = create_app()
    uvicorn.run(app, host=config.host, port=config.port, reload=True)


if __name__ == "__main__":
    run()
