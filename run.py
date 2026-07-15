#!/usr/bin/env python3
"""Run JARVIS web server."""

import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from jarvis.web.main import create_app, initialize_agents
from jarvis.core.config import get_config
from jarvis.core.database import get_db
from jarvis.workspace.manager import WorkspaceManager
import jarvis.web.main as web_main

async def init():
    """Initialize JARVIS components."""
    db = await get_db()
    initialize_agents()
    web_main.workspace_manager = WorkspaceManager()

if __name__ == "__main__":
    import uvicorn
    
    # Initialize before creating app
    asyncio.get_event_loop().run_until_complete(init())
    
    config = get_config()
    app = create_app()
    
    print(f"\n  JARVIS v2.0.0")
    print(f"  Running on http://{config.host}:{config.port}\n")
    
    uvicorn.run(app, host=config.host, port=config.port)
