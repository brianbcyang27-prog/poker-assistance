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
    
    # Restore agent states from database
    try:
        from jarvis.core.models import AgentState
        saved_states = await db.get_agent_states()
        for king in jarvis.get_all_kings():
            if king.card_id in saved_states:
                try:
                    king.state = AgentState(saved_states[king.card_id])
                except ValueError:
                    pass
    except Exception:
        pass  # Don't fail startup on state restoration errors
    
    # Load voice engine
    from jarvis.web.services.tts import voice_engine
    voice_engine.load()
    
    # Initialize workspace manager
    global workspace_manager
    workspace_manager = WorkspaceManager()
    
    # Auto-register JARVIS itself as a known project
    try:
        from jarvis.brain.project_memory import project_memory
        await project_memory.register_project(
            name="jarvis",
            path=str(Path(__file__).parent.parent.parent),
            description="JARVIS — Multi-Agent AI Operating System",
            language="python",
            server_command="python3 run.py",
            server_port=config.port,
            url=f"http://{config.host}:{config.port}",
            ai_tool_command="code /Users/brianyang/jarvis",
            ai_tool_name="VS Code",
        )
    except Exception:
        pass

    # v3.1: Register capabilities for existing tools
    try:
        from jarvis.core.capabilities import registry, Capability, CapType
        from jarvis.computer.controller import ComputerController
        ctrl = ComputerController.__new__(ComputerController)
        for action in ComputerController.ACTIONS if hasattr(ComputerController, 'ACTIONS') else []:
            pass  # Actions registered lazily on first use

        # Register known tool capabilities
        tool_caps = [
            ("browser_navigate", "♣K", "Navigate to a URL", ["web"]),
            ("browser_screenshot", "♣K", "Screenshot current page", ["web"]),
            ("browser_click", "♣K", "Click an element", ["web"]),
            ("browser_type", "♣K", "Type into an input", ["web"]),
            ("web_search", "♦K", "Search the web", ["web"]),
            ("web_fetch", "♦K", "Fetch and extract text", ["web"]),
            ("screen_capture", "♣K", "Capture the screen", ["screen"]),
            ("screen_get_active_window", "♣K", "Get active window", ["screen"]),
            ("shell_execute", "♣K", "Execute shell command", ["system"]),
            ("resume_project", "♣K", "Resume a project", ["project"]),
            ("register_project", "♣K", "Register a project", ["project"]),
        ]
        for name, owner, desc, tags in tool_caps:
            await registry.register(Capability(
                name=name, owner=owner, type=CapType.TOOL,
                description=desc, tags=tags,
            ))

        # Register worker capabilities
        for king in jarvis.get_all_kings():
            for worker in king.get_all_workers():
                await registry.register(Capability(
                    name=worker.card_id,
                    owner=king.card_id,
                    type=CapType.WORKER,
                    description=worker.name,
                    tags=[king.suit.value] if king.suit else [],
                ))
    except Exception:
        pass

    # v3.1: Emit startup event
    try:
        from jarvis.core.events import event_bus, Event
        await event_bus.emit(Event(
            type="system.started",
            data={"version": "3.1.0", "host": config.host, "port": config.port},
            source="system",
        ))
    except Exception:
        pass
    
    yield
    
    # Shutdown
    await db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="JARVIS",
        description="Multi-Agent AI Operating System",
        version="3.0.0",
        lifespan=lifespan,
    )
    
    # Mount static files
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Include routers
    from .routers import chat, agents, workspace, memory, voice, pages, websocket, settings, computer, iot, system
    app.include_router(chat.router)
    app.include_router(agents.router)
    app.include_router(workspace.router)
    app.include_router(memory.router)
    app.include_router(voice.router)
    app.include_router(pages.router)
    app.include_router(websocket.router)
    app.include_router(settings.router)
    app.include_router(computer.router)
    app.include_router(iot.router)
    app.include_router(system.router)
    
    return app


def run():
    """Run the JARVIS web server."""
    config = get_config()
    app = create_app()
    uvicorn.run(app, host=config.host, port=config.port, reload=True)


if __name__ == "__main__":
    run()
