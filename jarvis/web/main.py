"""JARVIS Web - FastAPI Application."""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from jarvis import __version__
from jarvis.agents.jarvis import JarvisAgent
from jarvis.agents.kings import EngineeringKing, PersonalKing, ResearchKing, SystemKing

# Architecture imports
from jarvis.architectures import (
    ArchitectureRegistry,
    HermesArchitecture,
    JarvisNativeArchitecture,
    get_architecture,
    get_settings_manager,
    list_architectures,
    set_architecture,
)
from jarvis.core.config import get_config
from jarvis.core.database import get_db
from jarvis.core.logging import get_logger, setup_logging
from jarvis.core.logging import log_config as log_cfg
from jarvis.workspace.manager import WorkspaceManager

# Global agent instances
jarvis: JarvisAgent = None
workspace_manager: WorkspaceManager = None
architecture_registry: ArchitectureRegistry = None
current_architecture = None


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

    return jarvis


async def _run_startup_diagnostics():
    """Run diagnostics in background and print results."""
    from jarvis.core.diagnostics import run_diagnostics
    from jarvis.core.logging import get_logger

    log = get_logger("jarvis.startup.diag")
    diag_results = await run_diagnostics()
    for r in diag_results:
        tag = "✓" if r.ok else "✗"
        rec = " [RECOVERED]" if r.recovered else ""
        print(f"  {tag} {r.name}: {r.message}{rec}")
    failed = [r for r in diag_results if not r.ok]
    if failed:
        unrecovered = [r for r in failed if not r.recovered]
        if unrecovered:
            print(
                f"\n  ⚠ [{len(unrecovered)}] Some subsystems degraded — "
                f"JARVIS will run with reduced capabilities\n"
            )
    log.info(
        "Startup diagnostics complete (%d checks, %d failures)", len(diag_results), len(failed)
    )


async def _register_capabilities():
    """Register tool, worker, and memory capabilities (non-blocking)."""
    from jarvis.core.capabilities import Capability, CapType, registry
    from jarvis.web.main import jarvis

    tool_caps = [
        ("browser_navigate", "♣K", "Navigate to a URL", ["web"], "browser"),
        ("browser_screenshot", "♣K", "Screenshot current page", ["web"], "browser"),
        ("browser_click", "♣K", "Click an element", ["web"], "browser"),
        ("browser_type", "♣K", "Type into an input", ["web"], "browser"),
        ("web_search", "♦K", "Search the web", ["web"], "tool"),
        ("web_fetch", "♦K", "Fetch and extract text", ["web"], "tool"),
        ("screen_capture", "♣K", "Capture the screen", ["screen"], "computer"),
        ("screen_get_active_window", "♣K", "Get active window", ["screen"], "computer"),
        ("shell_execute", "♣K", "Execute shell command", ["system"], "computer"),
        ("list_files", "♣K", "List files in a directory", ["files"], "computer"),
        ("read_file", "♣K", "Read file contents", ["files"], "computer"),
        ("write_file", "♣K", "Write content to a file", ["files"], "computer"),
        ("create_file", "♣K", "Create a new file", ["files"], "computer"),
        ("resume_project", "♣K", "Resume a project", ["project"], "tool"),
        ("register_project", "♣K", "Register a project", ["project"], "tool"),
    ]
    for name, owner, desc, tags, category in tool_caps:
        await registry.register(
            Capability(
                name=name,
                owner=owner,
                type=CapType.TOOL,
                description=desc,
                tags=tags,
                category=category,
            )
        )
    if jarvis:
        for king in jarvis.get_all_kings():
            for worker in king.get_all_workers():
                await registry.register(
                    Capability(
                        name=worker.card_id,
                        owner=king.card_id,
                        type=CapType.WORKER,
                        description=worker.name,
                        tags=[king.suit.value] if king.suit else [],
                        category="engineering",
                    )
                )
    memory_caps = [
        ("memory_episodes", "♥K", "Store and retrieve episodic memories", ["memory"], "memory"),
        ("memory_personal", "♥K", "Store and retrieve personal preferences", ["memory"], "memory"),
        ("memory_journal", "♥K", "Store and retrieve journal entries", ["memory"], "memory"),
        ("memory_working", "♥K", "Working memory for current context", ["memory"], "memory"),
        ("memory_graph", "♥K", "Search knowledge graph", ["memory"], "memory"),
    ]
    for name, owner, desc, tags, category in memory_caps:
        await registry.register(
            Capability(
                name=name,
                owner=owner,
                type=CapType.MEMORY,
                description=desc,
                tags=tags,
                category=category,
            )
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    import asyncio
    import time

    startup_start = time.time()
    config = get_config()

    # === LOGGING ===
    log_cfg.level = config.log_level
    if config.log_dir:
        log_cfg.log_dir = config.log_dir
    log_cfg.json_file = config.log_json_file
    log_cfg.json_max_bytes = config.log_json_max_bytes
    log_cfg.json_backup_count = config.log_json_backup_count
    log_cfg.console_output = config.log_console
    setup_logging()
    log = get_logger("jarvis.startup")

    # === START HEALTH MONITOR (continuous background checks) ===
    from jarvis.core.health_monitor import health_monitor

    await health_monitor.start()

    # === BACKGROUND STARTUP DIAGNOSTICS (non-blocking — prints as it completes) ===
    diag_task = asyncio.create_task(_run_startup_diagnostics())

    # === AUTH SETUP ===
    from jarvis.web.auth import auth_manager

    api_key = auth_manager.setup()
    if api_key:
        print(f"  🔑 API Key: {api_key[:12]}... (store securely)")

    # === DATABASE ===
    db = await get_db()

    # === AGENTS ===
    initialize_agents()

    # === ARCHITECTURES (background — don't block serve) ===
    import jarvis.architectures as arch_module

    global architecture_registry
    architecture_registry = arch_module._registry

    async def _init_architectures():
        """Initialize and register architectures in background."""
        try:
            native_arch = JarvisNativeArchitecture()
            await native_arch.initialize()
            architecture_registry.register(native_arch)

            hermes_arch = HermesArchitecture()
            await hermes_arch.initialize()
            architecture_registry.register(hermes_arch)

            settings_manager = get_settings_manager()
            settings = settings_manager.load()

            if settings.default_architecture:
                set_architecture(settings.default_architecture)
            else:
                set_architecture("jarvis_native")

            print(f"  ✓ Architectures initialized: {len(list_architectures())} registered")
            current_arch = get_architecture()
            if current_arch:
                print(f"  ✓ Active architecture: {current_arch.name}")
        except Exception as e:
            log.warning("Architecture init skipped: %s", e)

    asyncio.create_task(_init_architectures())

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

    # === VOICE ENGINE (loaded lazily on first voice API call) ===
    try:
        log.info("Voice engine registered (lazy-load)")
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

    # === BACKGROUND CAPABILITY REGISTRATION (non-blocking) ===
    asyncio.create_task(_register_capabilities())

    # === EMIT STARTUP EVENT ===
    try:
        from jarvis.core.events import Event, event_bus

        await event_bus.emit(
            Event(
                type="system.started",
                data={"version": __version__, "host": config.host, "port": config.port},
                source="system",
            )
        )
    except Exception as e:
        import logging

        logging.getLogger("jarvis.startup").debug(f"Startup event skipped: {e}")

    # Wait briefly for diagnostics to finish so "ready" prints last
    try:
        await asyncio.wait_for(asyncio.shield(diag_task), timeout=5.0)
    except TimeoutError:
        log.info("Startup diagnostics still running — will complete in background")

    elapsed = time.time() - startup_start
    print(f"  ✓ JARVIS v{__version__} ready ({elapsed:.1f}s)\n")

    # Record server-ready timing
    try:
        from jarvis.core.startup_timer import startup_timer

        startup_timer.mark("server_ready")
        log.info("Startup performance:\n%s", startup_timer.report())
    except Exception:
        pass

    # P0: Pre-warm LLM in background so first chat doesn't pay Ollama probe penalty
    async def _prewarm_llm():
        """Trigger the one-time Ollama probe in background."""
        try:
            await asyncio.sleep(2)  # Let server settle first
            from jarvis.brain.llm import llm

            ts = time.time()
            available = await llm.is_available()
            elapsed_pw = time.time() - ts
            log.info("LLM pre-warm complete: available=%s (%.2fs)", available, elapsed_pw)
        except Exception:
            pass

    asyncio.create_task(_prewarm_llm())

    yield

    # === SHUTDOWN ===
    # Stop health monitor
    await health_monitor.stop()

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
    get_config()

    app = FastAPI(
        title="JARVIS",
        description="Multi-Agent AI Operating System",
        version=__version__,
        lifespan=lifespan,
    )

    # Mount static files (no-cache for development)

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

    # Authentication middleware (protects all /api/* endpoints)
    from jarvis.web.auth import AuthMiddleware

    app.add_middleware(AuthMiddleware)

    # Global rate limiter for POST/PUT/PATCH
    from jarvis.web.rate_limit_middleware import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware, max_post=30, window=60)

    # Include routers
    from .api import mission_replay
    from .routers import (
        agents,
        auth,
        chat,
        checkpoints,
        computer,
        engineering,
        iot,
        memory,
        pages,
        security,
        settings,
        system,
        voice,
        websocket,
        workspace,
        world,
    )

    app.include_router(auth.router)
    app.include_router(checkpoints.router)
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
    uvicorn.run(app, host=config.host, port=config.port)


if __name__ == "__main__":
    run()


app = create_app()
