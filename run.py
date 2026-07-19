#!/usr/bin/env python3
"""Run JARVIS web server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from jarvis.web.main import create_app
from jarvis.core.config import get_config

if __name__ == "__main__":
    import uvicorn

    config = get_config()
    app = create_app()

    from jarvis import __version__
    print(f"\n  JARVIS v{__version__}")
    print(f"  Running on http://{config.host}:{config.port}\n")

    uvicorn.run(app, host=config.host, port=config.port)
