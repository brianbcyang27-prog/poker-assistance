#!/usr/bin/env python3
"""Run JARVIS web server."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from jarvis.core.config import get_config
from jarvis.web.main import create_app


def cleanup_port(port: int):
    """Kill any process listening on the given port."""
    try:
        result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                subprocess.run(["kill", "-9", pid], capture_output=True)
            print(f"  ✓ Cleaned up port {port} (killed PIDs: {', '.join(pids)})")
    except Exception:
        pass  # Ignore errors


if __name__ == "__main__":
    import uvicorn

    config = get_config()

    # Clean up any existing process on the port
    cleanup_port(config.port)

    app = create_app()

    from jarvis import __version__

    print(f"\n  JARVIS v{__version__}")
    print(f"  Running on http://{config.host}:{config.port}\n")

    uvicorn.run(app, host=config.host, port=config.port)
