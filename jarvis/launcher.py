"""JARVIS Native Launcher — Single command to start everything.

Usage:
    jarvis              # Launch JARVIS (check deps, start server, open browser)
    jarvis doctor       # Run system health checks
    jarvis status       # Quick status
    jarvis server       # Start server only (no browser)
"""

import os
import sys
import time
import signal
import subprocess
import urllib.request
import urllib.error
import webbrowser
import importlib
import importlib.metadata
from pathlib import Path
from typing import Optional


# ── ANSI Colors ──────────────────────────────────────────────────────────────

class _C:
    """ANSI color codes."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GOLD    = "\033[38;5;220m"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ok(msg: str) -> str:
    return f"{_C.GREEN}✓{_C.RESET} {msg}"

def _warn(msg: str) -> str:
    return f"{_C.YELLOW}⚠{_C.RESET} {msg}"

def _fail(msg: str) -> str:
    return f"{_C.RED}✗{_C.RESET} {msg}"

def _info(msg: str) -> str:
    return f"{_C.DIM}{msg}{_C.RESET}"

def _step(step: int, total: int, msg: str) -> str:
    return f"  {_C.CYAN}[{step}/{total}]{_C.RESET} {msg}"


# ── Check Functions ──────────────────────────────────────────────────────────

def check_python() -> tuple[bool, str]:
    """Check Python version."""
    v = sys.version_info
    if v >= (3, 11):
        return True, f"Python {v.major}.{v.minor}.{v.micro}"
    return False, f"Python {v.major}.{v.minor}.{v.micro} (need 3.11+)"


def check_dependencies() -> tuple[bool, str]:
    """Check required packages."""
    required = [
        "fastapi", "uvicorn", "pydantic", "dotenv",
        "aiosqlite", "jinja2", "websockets", "rich",
    ]
    missing = []
    for pkg in required:
        try:
            importlib.import_name(pkg if pkg != "dotenv" else "dotenv")
        except ImportError:
            missing.append(pkg)
    if missing:
        return False, f"Missing: {', '.join(missing)}"
    return True, f"{len(required)} packages installed"


def check_database(db_path: str = "jarvis.db") -> tuple[bool, str]:
    """Check SQLite database."""
    p = Path(db_path)
    if p.exists():
        size_mb = p.stat().st_size / (1024 * 1024)
        return True, f"Database: {size_mb:.1f} MB"
    return False, "Database not found (will be created on first run)"


def check_config() -> tuple[bool, str]:
    """Check .env configuration."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return False, ".env file not found"

    has_key = False
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            if "API_KEY" in k and v.strip():
                has_key = True
                break

    if has_key:
        return True, "API key configured"
    return False, "No API key found in .env"


def check_port(port: int = 8000) -> tuple[bool, str]:
    """Check if port is available or already in use."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return True, f"Port {port} available"
    except OSError:
        # Port in use — check if it's JARVIS
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/health",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return True, f"Port {port} — JARVIS already running"
        except Exception:
            pass
        return False, f"Port {port} in use by another process"
    finally:
        sock.close()


def check_voice() -> tuple[bool, str]:
    """Check voice services availability."""
    try:
        import importlib
        importlib.import_module("jarvis.voice.tts")
        return True, "Voice services available"
    except ImportError:
        return False, "Voice services not installed (optional)"


def check_browser_tools() -> tuple[bool, str]:
    """Check browser automation tools."""
    try:
        import playwright
        return True, "Playwright available"
    except ImportError:
        pass
    try:
        import subprocess
        result = subprocess.run(
            ["playwright", "install", "--dry-run"],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            return True, "Playwright CLI available"
    except Exception:
        pass
    return False, "Playwright not installed (optional)"


# ── Health Check Runner ──────────────────────────────────────────────────────

def run_checks(server_port: int = 8000) -> list[tuple[bool, str, str]]:
    """Run all startup checks. Returns list of (ok, name, detail)."""
    checks = []

    ok, detail = check_python()
    checks.append((ok, "Python", detail))

    ok, detail = check_dependencies()
    checks.append((ok, "Dependencies", detail))

    ok, detail = check_database()
    checks.append((ok, "Database", detail))

    ok, detail = check_config()
    checks.append((ok, "Configuration", detail))

    ok, detail = check_port(server_port)
    checks.append((ok, "Port", detail))

    ok, detail = check_voice()
    checks.append((ok, "Voice", detail))

    ok, detail = check_browser_tools()
    checks.append((ok, "Browser", detail))

    return checks


# ── Server Management ────────────────────────────────────────────────────────

def is_server_running(port: int = 8000) -> bool:
    """Check if JARVIS server is already running."""
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/health",
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def wait_for_server(port: int = 8000, timeout: float = 30.0) -> bool:
    """Wait until server is healthy."""
    start = time.time()
    while time.time() - start < timeout:
        if is_server_running(port):
            return True
        time.sleep(0.5)
    return False


def start_server(port: int = 8000) -> subprocess.Popen:
    """Start JARVIS server as a subprocess."""
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "jarvis.web.main:app",
         "--host", "0.0.0.0", "--port", str(port)],
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ── Main Launcher ────────────────────────────────────────────────────────────

def launch(port: int = 8000, open_browser: bool = True) -> None:
    """The main JARVIS launcher. Single command to start everything."""
    from jarvis import __version__

    print()
    print(f"  {_C.GOLD}JARVIS{_C.RESET} {_C.DIM}v{__version__}{_C.RESET}")
    print(f"  {_C.DIM}Personal AI Operating System{_C.RESET}")
    print()

    total = 7
    checks = run_checks(port)

    for i, (ok, name, detail) in enumerate(checks, 1):
        if ok:
            print(_step(i, total, _ok(f"{name}: {detail}")))
        else:
            print(_step(i, total, _warn(f"{name}: {detail}")))

    print()

    # Check for critical failures
    critical = [c for i, (ok, name, detail) in enumerate(checks) if not ok and i < 4]
    if critical:
        print(f"  {_C.RED}Cannot start — critical checks failed{_C.RESET}")
        print(f"  {_C.DIM}Run 'jarvis doctor' for details{_C.RESET}")
        print()
        sys.exit(1)

    # Start or connect to server
    already_running = is_server_running(port)

    if already_running:
        print(f"  {_C.GREEN}→{_C.RESET} JARVIS already running on port {port}")
    else:
        print(f"  {_C.CYAN}→{_C.RESET} Starting JARVIS server...")
        proc = start_server(port)

        # Handle Ctrl+C gracefully
        def _shutdown(sig, frame):
            print(f"\n  {_C.DIM}Shutting down...{_C.RESET}")
            proc.terminate()
            proc.wait(timeout=5)
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        if wait_for_server(port, timeout=15):
            elapsed = "ready"
            print(f"  {_C.GREEN}→{_C.RESET} Server healthy on port {port}")
        else:
            print(f"  {_C.YELLOW}→{_C.RESET} Server started but health check timed out")
            print(f"  {_C.DIM}  Try opening http://127.0.0.1:{port} manually{_C.RESET}")

    # Open browser
    if open_browser:
        url = f"http://127.0.0.1:{port}"
        print(f"  {_C.CYAN}→{_C.RESET} Opening {url}")
        webbrowser.open(url)

    print()
    print(f"  {_C.DIM}Press Ctrl+C to stop{_C.RESET}")
    print()

    # Keep the launcher alive if we started the server
    if not already_running:
        try:
            proc.wait()
        except KeyboardInterrupt:
            print(f"\n  {_C.DIM}Shutting down...{_C.RESET}")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


# ── Doctor Command ───────────────────────────────────────────────────────────

def doctor() -> None:
    """Run comprehensive system health checks."""
    from jarvis import __version__

    print()
    print(f"  {_C.GOLD}JARVIS Doctor{_C.RESET} {_C.DIM}v{__version__}{_C.RESET}")
    print()

    checks = run_checks()

    # Additional deep checks
    try:
        import asyncio
        from jarvis.doctor import run_doctor
        results = asyncio.run(run_doctor())
        for r in results:
            icon = {"ok": f"{_C.GREEN}✓", "warn": f"{_C.YELLOW}⚠", "fail": f"{_C.RED}✗"}[r.status]
            print(f"  {icon} {r.status.upper():5}{_C.RESET} {r.name}: {r.message}")
    except Exception as e:
        print(f"  {_C.YELLOW}⚠{_C.RESET} Deep checks skipped: {e}")

    print()
    print(f"  {_C.DIM}Run 'jarvis' to start the server{_C.RESET}")
    print()


# ── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    """CLI entry point for 'jarvis' command."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="jarvis",
        description="JARVIS — Personal AI Operating System",
    )
    parser.add_argument(
        "command", nargs="?", default="launch",
        choices=["launch", "doctor", "status", "server", "stop"],
        help="Command to run (default: launch)",
    )
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    parser.add_argument("--cli", action="store_true", help="Legacy TUI mode")

    args = parser.parse_args()

    if args.command == "launch":
        launch(port=args.port, open_browser=not args.no_browser)
    elif args.command == "doctor":
        doctor()
    elif args.command == "status":
        from jarvis import __version__
        running = is_server_running(args.port)
        status = f"{_C.GREEN}running{_C.RESET}" if running else f"{_C.RED}stopped{_C.RESET}"
        print(f"\n  JARVIS v{__version__} — {status}\n")
    elif args.command == "server":
        import uvicorn
        from jarvis.core.config import get_config
        config = get_config()
        uvicorn.run("jarvis.web.main:app", host=config.host, port=config.port)
    elif args.command == "stop":
        if is_server_running(args.port):
            print(f"  {_C.DIM}Stopping JARVIS...{_C.RESET}")
            # Send SIGTERM to uvicorn processes
            import subprocess
            subprocess.run(["pkill", "-f", f"uvicorn.*jarvis.*{args.port}"],
                         capture_output=True)
            print(f"  {_C.GREEN}✓{_C.RESET} Stopped")
        else:
            print(f"  {_C.DIM}JARVIS is not running{_C.RESET}")
    elif args.cli:
        # Legacy TUI mode
        from jarvis.cli import JARVISTUI
        tui = JARVISTUI()
        tui.run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
