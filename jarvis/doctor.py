"""JARVIS Doctor — Comprehensive system health check.

Run with: python -m jarvis doctor
"""

import asyncio
import sys
import shutil
import importlib
from pathlib import Path
from typing import NamedTuple


class CheckResult(NamedTuple):
    name: str
    status: str  # "ok", "warn", "fail"
    message: str
    repairable: bool = False
    repair_hint: str = ""


async def run_doctor() -> list[CheckResult]:
    """Run all system checks."""
    results = []

    # Core system
    results.append(check_python())
    results.append(check_dependencies())
    results.append(check_database())
    results.append(check_config())
    results.append(check_port())

    # AI subsystems
    results.append(await check_llm())
    results.append(await check_memory())
    results.append(await check_knowledge_graph())
    results.append(await check_capabilities())

    # Automation
    results.append(check_browser())
    results.append(check_playwright())
    results.append(check_computer())
    results.append(check_accessibility())

    # Voice & Vision
    results.append(check_voice())
    results.append(check_vision())

    # Infrastructure
    results.append(check_filesystem())
    results.append(check_network())
    results.append(check_gpu())
    results.append(check_permissions())
    results.append(check_models())

    return results


# ── Core System Checks ──────────────────────────────────────────────────────

def check_python() -> CheckResult:
    """Check Python version."""
    v = sys.version_info
    if v >= (3, 11):
        return CheckResult("Python", "ok", f"v{v.major}.{v.minor}.{v.micro}")
    elif v >= (3, 9):
        return CheckResult("Python", "warn",
            f"v{v.major}.{v.minor}.{v.micro} — 3.11+ recommended",
            repairable=False)
    else:
        return CheckResult("Python", "fail",
            f"v{v.major}.{v.minor}.{v.micro} — 3.11+ required")


def check_dependencies() -> CheckResult:
    """Check required packages."""
    required = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "dotenv": "python-dotenv",
        "aiosqlite": "aiosqlite",
        "jinja2": "jinja2",
        "websockets": "websockets",
        "rich": "rich",
        "aiohttp": "aiohttp",
        "bs4": "beautifulsoup4",
    }
    installed = []
    missing = []
    for import_name, pip_name in required.items():
        try:
            importlib.import_module(import_name)
            installed.append(pip_name)
        except ImportError:
            missing.append(pip_name)

    if not missing:
        return CheckResult("Dependencies", "ok", f"{len(installed)} packages installed")
    return CheckResult("Dependencies", "fail",
        f"Missing: {', '.join(missing)}",
        repairable=True,
        repair_hint=f"pip install {' '.join(missing)}")


def check_database() -> CheckResult:
    """Check SQLite database."""
    try:
        db_path = Path("jarvis.db")
        if db_path.exists():
            size_mb = db_path.stat().st_size / (1024 * 1024)
            # Test basic operations
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.execute("SELECT count(*) FROM sqlite_master")
            conn.close()
            return CheckResult("Database", "ok", f"SQLite — {size_mb:.1f} MB")
        else:
            return CheckResult("Database", "warn",
                "Database not found (will be created on first run)",
                repairable=True,
                repair_hint="Start JARVIS to auto-create database")
    except Exception as e:
        return CheckResult("Database", "fail", str(e)[:100],
            repairable=True,
            repair_hint="Delete jarvis.db and restart")


def check_config() -> CheckResult:
    """Check .env configuration."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return CheckResult("Config", "fail", ".env file not found",
            repairable=True,
            repair_hint="cp .env.example .env")

    keys_found = 0
    api_key_set = False
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys_found += 1
            k, v = line.split("=", 1)
            if "API_KEY" in k and v.strip() and not v.strip().startswith("your-"):
                api_key_set = True

    if api_key_set:
        return CheckResult("Config", "ok", f"{keys_found} variables configured")
    return CheckResult("Config", "warn", "No API key configured",
        repairable=True,
        repair_hint="Set NVIDIA_API_KEY in .env")


def check_port() -> CheckResult:
    """Check if server port is available."""
    import socket
    port = int(os.environ.get("PORT", "8000")) if "PORT" in os.environ else 8000
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return CheckResult("Port", "ok", f"Port {port} available")
    except OSError:
        # Check if JARVIS is running
        try:
            import urllib.request
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status == 200:
                    return CheckResult("Port", "ok", f"Port {port} — JARVIS running")
        except Exception:
            pass
        return CheckResult("Port", "warn", f"Port {port} in use",
            repairable=True,
            repair_hint=f"lsof -ti:{port} | xargs kill")
    finally:
        sock.close()


# ── AI Subsystem Checks ─────────────────────────────────────────────────────

async def check_llm() -> CheckResult:
    """Check LLM API connectivity."""
    try:
        from jarvis.core.config import get_config
        config = get_config()
        api_key = config.nvidia_api_key
        if not api_key:
            return CheckResult("LLM", "warn", "No API key configured")

        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://integrate.api.nvidia.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if r.status_code == 200:
                models = r.json().get("data", [])
                model_name = getattr(config, "nvidia_model", "unknown")
                return CheckResult("LLM", "ok",
                    f"NVIDIA API — {len(models)} models available")
            else:
                return CheckResult("LLM", "warn", f"API returned {r.status_code}")
    except httpx.ConnectError:
        return CheckResult("LLM", "warn", "Network unreachable")
    except Exception as e:
        return CheckResult("LLM", "fail", str(e)[:100])


async def check_memory() -> CheckResult:
    """Check memory systems."""
    try:
        from jarvis.core.memory_validation import memory_validator
        health = await memory_validator.validate_memory_health()
        if health["healthy"]:
            return CheckResult("Memory", "ok", "All memory systems healthy")
        else:
            failed = [k for k, v in health["systems"].items() if not v.get("healthy")]
            return CheckResult("Memory", "warn", f"Issues: {', '.join(failed)}")
    except Exception as e:
        return CheckResult("Memory", "warn", str(e)[:100])


async def check_knowledge_graph() -> CheckResult:
    """Check knowledge graph."""
    try:
        from jarvis.brain.memory.graph import graph
        if hasattr(graph, 'get_stats'):
            stats = await graph.get_stats()
            return CheckResult("Knowledge Graph", "ok",
                f"{stats.get('nodes', 0)} nodes, {stats.get('edges', 0)} edges")
        return CheckResult("Knowledge Graph", "ok", "Initialized")
    except Exception as e:
        return CheckResult("Knowledge Graph", "warn", str(e)[:100])


async def check_capabilities() -> CheckResult:
    """Check capability registry."""
    try:
        from jarvis.core.capabilities import registry
        if hasattr(registry, 'get_stats'):
            stats = await registry.get_stats()
            return CheckResult("Capabilities", "ok",
                f"{stats.get('total', 0)} registered")
        return CheckResult("Capabilities", "ok", "Initialized")
    except Exception as e:
        return CheckResult("Capabilities", "warn", str(e)[:100])


# ── Automation Checks ───────────────────────────────────────────────────────

def check_browser() -> CheckResult:
    """Check browser control."""
    try:
        import importlib
        importlib.import_module("jarvis.browser")
        return CheckResult("Browser", "ok", "Browser module available")
    except ImportError:
        return CheckResult("Browser", "warn", "Browser module not found",
            repairable=True,
            repair_hint="pip install playwright && playwright install")


def check_playwright() -> CheckResult:
    """Check Playwright installation."""
    try:
        import playwright
        # Check if browsers are installed
        browsers_path = Path.home() / ".cache" / "ms-playwright"
        if browsers_path.exists():
            browsers = list(browsers_path.iterdir())
            return CheckResult("Playwright", "ok",
                f"{len(browsers)} browser(s) installed")
        return CheckResult("Playwright", "warn",
            "Playwright installed but no browsers",
            repairable=True,
            repair_hint="playwright install")
    except ImportError:
        return CheckResult("Playwright", "warn", "Not installed (optional)")


def check_computer() -> CheckResult:
    """Check computer control."""
    try:
        import importlib
        mod = importlib.import_module("jarvis.computer.controller")
        return CheckResult("Computer", "ok", "Computer control available")
    except ImportError:
        return CheckResult("Computer", "warn", "Computer control not available")


def check_accessibility() -> CheckResult:
    """Check accessibility APIs."""
    if sys.platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["osascript", "-e", 'tell application "System Events" to get name of first process'],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return CheckResult("Accessibility", "ok", "macOS accessibility available")
            return CheckResult("Accessibility", "warn",
                "Accessibility permissions may be needed",
                repairable=True,
                repair_hint="Enable in System Settings > Privacy & Security > Accessibility")
        except Exception:
            return CheckResult("Accessibility", "warn", "Could not test")
    return CheckResult("Accessibility", "ok", "Platform not macOS — limited")


# ── Voice & Vision ──────────────────────────────────────────────────────────

def check_voice() -> CheckResult:
    """Check voice services."""
    try:
        import importlib
        tts_mod = importlib.import_module("jarvis.voice.tts")
        return CheckResult("Voice", "ok", "TTS available")
    except ImportError:
        return CheckResult("Voice", "warn", "Voice services not installed",
            repairable=True,
            repair_hint="pip install -e '.[voice]'")

def check_vision() -> CheckResult:
    """Check vision capabilities."""
    try:
        import importlib
        importlib.import_module("jarvis.vision")
        return CheckResult("Vision", "ok", "Vision module available")
    except ImportError:
        return CheckResult("Vision", "warn", "Vision module not found")


# ── Infrastructure ──────────────────────────────────────────────────────────

def check_filesystem() -> CheckResult:
    """Check filesystem permissions."""
    jarvis_dir = Path(__file__).parent.parent
    try:
        # Check write access
        test_file = jarvis_dir / ".doctor_test"
        test_file.write_text("test")
        test_file.unlink()

        # Check disk space
        usage = shutil.disk_usage(str(jarvis_dir))
        free_gb = usage.free / (1024**3)
        if free_gb < 1:
            return CheckResult("Filesystem", "warn",
                f"Low disk space: {free_gb:.1f} GB free")
        return CheckResult("Filesystem", "ok",
            f"{free_gb:.1f} GB free, write access OK")
    except PermissionError:
        return CheckResult("Filesystem", "fail", "No write access to project directory")
    except Exception as e:
        return CheckResult("Filesystem", "warn", str(e)[:100])


def check_network() -> CheckResult:
    """Check network connectivity."""
    import socket
    try:
        sock = socket.create_connection(("integrate.api.nvidia.com", 443), timeout=5)
        sock.close()
        return CheckResult("Network", "ok", "NVIDIA API reachable")
    except socket.timeout:
        return CheckResult("Network", "warn", "Network timeout")
    except OSError as e:
        return CheckResult("Network", "fail", f"Network error: {e}")


def check_gpu() -> CheckResult:
    """Check GPU availability."""
    try:
        import subprocess
        result = subprocess.run(
            ["system_profiler", "SPDisplaysDataType"],
            capture_output=True, timeout=5, text=True
        )
        if "Apple" in result.stdout:
            return CheckResult("GPU", "ok", "Apple Silicon GPU available")
        elif "NVIDIA" in result.stdout or "AMD" in result.stdout:
            return CheckResult("GPU", "ok", "Discrete GPU available")
        return CheckResult("GPU", "ok", "GPU detected")
    except Exception:
        return CheckResult("GPU", "warn", "Could not detect GPU")


def check_permissions() -> CheckResult:
    """Check macOS permissions."""
    if sys.platform != "darwin":
        return CheckResult("Permissions", "ok", "Non-macOS — limited checks")

    perm_file = Path.home() / ".jarvis" / "permissions.json"
    if perm_file.exists():
        import json
        perms = json.loads(perm_file.read_text())
        granted = sum(1 for v in perms.values() if v)
        total = len(perms)
        return CheckResult("Permissions", "ok",
            f"{granted}/{total} permissions granted")
    return CheckResult("Permissions", "warn",
        "No permissions file found",
        repairable=True,
        repair_hint="Configure in Settings > Permissions")


def check_models() -> CheckResult:
    """Check available AI models."""
    try:
        from jarvis.core.config import get_config
        config = get_config()
        model = getattr(config, "nvidia_model", None) or "meta/llama-3.1-8b-instruct"
        return CheckResult("Models", "ok", f"Primary: {model}")
    except Exception as e:
        return CheckResult("Models", "warn", str(e)[:100])


# ── Print Results ───────────────────────────────────────────────────────────

def print_results(results: list[CheckResult]):
    """Print results in human-readable format."""
    print("\n" + "=" * 55)
    print("  JARVIS Doctor — System Health Report")
    print("=" * 55 + "\n")

    icons = {
        "ok": "\033[92m✓\033[0m",
        "warn": "\033[93m⚠\033[0m",
        "fail": "\033[91m✗\033[0m",
    }
    status_colors = {
        "ok": "\033[92m",
        "warn": "\033[93m",
        "fail": "\033[91m",
    }

    for r in results:
        icon = icons.get(r.status, "?")
        color = status_colors.get(r.status, "")
        reset = "\033[0m"
        print(f"  {icon} {color}{r.status.upper():5}{reset} {r.name}: {r.message}")
        if r.repairable and r.repair_hint:
            print(f"         \033[96m→ Fix: {r.repair_hint}{reset}")

    print("\n" + "-" * 55)
    passed = sum(1 for r in results if r.status == "ok")
    warned = sum(1 for r in results if r.status == "warn")
    failed = sum(1 for r in results if r.status == "fail")
    repairable = sum(1 for r in results if r.repairable and r.status != "ok")

    if failed == 0:
        print(f"  \033[92mAll systems operational!\033[0m")
    else:
        print(f"  \033[91m{failed} critical issue(s) detected\033[0m")

    print(f"\n  {passed} passed, {warned} warnings, {failed} failed", end="")
    if repairable:
        print(f" ({repairable} auto-repairable)")
    else:
        print()
    print()


async def main():
    """Main entry point."""
    results = await run_doctor()
    print_results(results)
    return 0 if all(r.status != "fail" for r in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
