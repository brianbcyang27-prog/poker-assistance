"""JARVIS CLI entry point.

Run with: python -m jarvis [command]
"""

import sys
import asyncio


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m jarvis [command]")
        print("Commands:")
        print("  doctor    - Run system health check")
        print("  server    - Start the server")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "doctor":
        from jarvis.doctor import main as doctor_main
        sys.exit(asyncio.run(doctor_main()))
    elif command == "server":
        import uvicorn
        from jarvis.core.config import get_config
        config = get_config()
        uvicorn.run(
            "jarvis.web.main:app",
            host=config.host,
            port=config.port,
            reload=False,
        )
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
