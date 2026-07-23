"""JARVIS Web - FastAPI Application."""

import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jarvis import __version__
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
    import time
    startup_start = time.time()
    config = get_config()

    # === STARTUP SELF-DEBUG ===
    from jarvis.core.diagnostics import run_diagnostics
    diag_results = await run_diagnostics()

    failed = [r for r in diag_results if not r.ok]
    recovered = [r for r in diag_results if r.recovered]

    for r in diag_results:
        tag = "✓" if r.ok else "✗"
        rec = " [RECOVERED]" if r.recovered else ""
        print(f"  {tag} {r.name}: {r.message}{rec}")

    if failed:
        unrecovered = [r for r in failed if not r.recovered]
        if unrecovered:
            print(f"\n  ⚠ {len(unrecovered)} subsystem(s) unhealthy — JARVIS will run with degraded capabilities\n")

    # === DATABASE ===
    db = await get_db()

    # === AGENTS ===
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
    except Exception as e:
        import logging
        logging.getLogger("jarvis.startup").debug(f"Agent state restore skipped: {e}")

    # === VOICE ENGINE ===
    try:
        from jarvis.web.services.tts import voice_engine
        voice_engine.load()
    except Exception as e:
        print(f"  ⚠ Voice engine: {e}")

    # === WORKSPACE MANAGER ===
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
            ai_tool_command=f"code {Path(__file__).parent.parent.parent}",
            ai_tool_name="VS Code",
        )
    except Exception as e:
        import logging
        logging.getLogger("jarvis.startup").debug(f"Project registration skipped: {e}")

    # === CAPABILITIES ===
    try:
        from jarvis.core.capabilities import registry, Capability, CapType
        tool_caps = [
            # Browser Control
            ("browser_navigate", "♣K", "Navigate to a URL", ["web"], "browser"),
            ("browser_screenshot", "♣K", "Screenshot current page", ["web"], "browser"),
            ("browser_click", "♣K", "Click an element", ["web"], "browser"),
            ("browser_type", "♣K", "Type into an input", ["web"], "browser"),
            # Web Research
            ("web_search", "♦K", "Search the web", ["web"], "tool"),
            ("web_fetch", "♦K", "Fetch and extract text", ["web"], "tool"),
            # Computer Control
            ("screen_capture", "♣K", "Capture the screen", ["screen"], "computer"),
            ("screen_get_active_window", "♣K", "Get active window", ["screen"], "computer"),
            ("shell_execute", "♣K", "Execute shell command", ["system"], "computer"),
            # Projects
            ("resume_project", "♣K", "Resume a project", ["project"], "tool"),
            ("register_project", "♣K", "Register a project", ["project"], "tool"),
        ]
        for name, owner, desc, tags, category in tool_caps:
            await registry.register(Capability(
                name=name, owner=owner, type=CapType.TOOL,
                description=desc, tags=tags, category=category,
            ))
        for king in jarvis.get_all_kings():
            for worker in king.get_all_workers():
                await registry.register(Capability(
                    name=worker.card_id,
                    owner=king.card_id,
                    type=CapType.WORKER,
                    description=worker.name,
                    tags=[king.suit.value] if king.suit else [],
                    category="engineering",
                ))
        
        # Memory capabilities
        memory_caps = [
            ("memory_episodes", "♥K", "Store and retrieve episodic memories", ["memory"], "memory"),
            ("memory_personal", "♥K", "Store and retrieve personal preferences", ["memory"], "memory"),
            ("memory_journal", "♥K", "Store and retrieve journal entries", ["memory"], "memory"),
            ("memory_working", "♥K", "Working memory for current context", ["memory"], "memory"),
            ("memory_graph", "♥K", "Search knowledge graph", ["memory"], "memory"),
        ]
        for name, owner, desc, tags, category in memory_caps:
            await registry.register(Capability(
                name=name, owner=owner, type=CapType.MEMORY,
                description=desc, tags=tags, category=category,
            ))
    except Exception as e:
        import logging
        logging.getLogger("jarvis.startup").debug(f"Capability registration skipped: {e}")

    # === EMIT STARTUP EVENT ===
    try:
        from jarvis.core.events import event_bus, Event
        await event_bus.emit(Event(
            type="system.started",
            data={"version": __version__, "host": config.host, "port": config.port},
            source="system",
        ))
    except Exception as e:
        import logging
        logging.getLogger("jarvis.startup").debug(f"Startup event skipped: {e}")

    elapsed = time.time() - startup_start
    print(f"  ✓ JARVIS v{__version__} ready ({elapsed:.1f}s)\n")

    yield

    # === SHUTDOWN ===
    # Cancel WebSocket bridge tasks
    try:
        from .routers.websocket import _bridge_tasks
        for t in _bridge_tasks:
            if not t.done():
                t.cancel()
        _bridge_tasks.clear()
    except Exception:
        pass
    
    # Close database
    await db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = get_config()
    
    app = FastAPI(
        title="JARVIS",
        description="Multi-Agent AI Operating System",
        version=__version__,
        lifespan=lifespan,
    )
    
    # Mount static files (no-cache for development)
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response
    
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    @app.middleware("http")
    async def no_cache_static(request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # Global rate limiter for POST/PUT/PATCH
    from jarvis.web.rate_limit_middleware import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, max_post=30, window=60)
    
    # Include routers
    from .routers import chat, agents, workspace, memory, voice, pages, websocket, settings, computer, iot, system, engineering, world, security
    from .api import mission_replay
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
    app.include_router(engineering.router)
    app.include_router(mission_replay.router)
    app.include_router(world.router)
    app.include_router(security.router)
    
    return app


def run():
    """Run the JARVIS web server."""
    config = get_config()
    app = create_app()
    uvicorn.run(app, host=config.host, port=config.port, reload=True)


if __name__ == "__main__":
    run()


app = create_app()
