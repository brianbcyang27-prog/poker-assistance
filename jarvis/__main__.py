"""JARVIS CLI entry point.

Run with: python -m jarvis [command]

Commands:
    (none)      Launch JARVIS — start server + open browser
    doctor      Run system health checks
    server      Start server only (no browser)
    status      Quick status check
    stop        Stop running server
"""

from jarvis.launcher import main

if __name__ == "__main__":
    main()
