"""JARVIS Doctor — System health check command.

Run with: python -m jarvis doctor
"""

import asyncio
import sys
from typing import NamedTuple


class CheckResult(NamedTuple):
    name: str
    status: str  # "ok", "warn", "fail"
    message: str


async def run_doctor() -> list[CheckResult]:
    """Run all system checks."""
    results = []
    
    # 1. Database
    results.append(await check_database())
    
    # 2. LLM
    results.append(await check_llm())
    
    # 3. Memory
    results.append(await check_memory())
    
    # 4. Browser
    results.append(await check_browser())
    
    # 5. Computer
    results.append(await check_computer())
    
    # 6. Accessibility
    results.append(await check_accessibility())
    
    # 7. Voice
    results.append(await check_voice())
    
    # 8. Frontend
    results.append(await check_frontend())
    
    # 9. WebSocket
    results.append(await check_websocket())
    
    return results


async def check_database() -> CheckResult:
    """Check database connectivity."""
    try:
        from jarvis.core.database import get_db
        db = await get_db()
        # Try a simple operation
        await db.get_session_count()
        return CheckResult("Database", "ok", "SQLite responsive")
    except Exception as e:
        return CheckResult("Database", "fail", str(e)[:100])


async def check_llm() -> CheckResult:
    """Check LLM API connectivity."""
    try:
        from jarvis.core.config import get_config
        config = get_config()
        api_key = config.nvidia_api_key
        if not api_key:
            return CheckResult("LLM", "warn", "No NVIDIA API key configured")
        
        # Test API
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://integrate.api.nvidia.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if r.status_code == 200:
                return CheckResult("LLM", "ok", "NVIDIA API reachable")
            else:
                return CheckResult("LLM", "warn", f"API returned {r.status_code}")
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
        return CheckResult("Memory", "fail", str(e)[:100])


async def check_browser() -> CheckResult:
    """Check browser control."""
    try:
        from jarvis.computer.controller import controller
        result = await controller.execute("browser_screenshot")
        if result.get("ok"):
            return CheckResult("Browser", "ok", "Browser control available")
        else:
            return CheckResult("Browser", "warn", "Browser control limited")
    except Exception as e:
        return CheckResult("Browser", "warn", str(e)[:100])


async def check_computer() -> CheckResult:
    """Check computer control."""
    try:
        from jarvis.computer.controller import controller
        result = await controller.execute("screen_capture")
        if result.get("ok"):
            return CheckResult("Computer", "ok", "Screen capture available")
        else:
            return CheckResult("Computer", "warn", "Screen capture limited")
    except Exception as e:
        return CheckResult("Computer", "warn", str(e)[:100])


async def check_accessibility() -> CheckResult:
    """Check accessibility control."""
    try:
        from jarvis.computer.controller import controller
        result = await controller.execute("screen_get_active_window")
        if result.get("ok"):
            return CheckResult("Accessibility", "ok", "Accessibility available")
        else:
            return CheckResult("Accessibility", "warn", "Accessibility limited")
    except Exception as e:
        return CheckResult("Accessibility", "warn", str(e)[:100])


async def check_voice() -> CheckResult:
    """Check voice systems."""
    try:
        from jarvis.voice.tts import get_tts
        tts = get_tts()
        return CheckResult("Voice", "ok", "TTS available")
    except Exception as e:
        return CheckResult("Voice", "warn", str(e)[:100])


async def check_frontend() -> CheckResult:
    """Check frontend serving."""
    try:
        from pathlib import Path
        static_dir = Path(__file__).parent / "web" / "static"
        if static_dir.exists():
            return CheckResult("Frontend", "ok", "Static files present")
        else:
            return CheckResult("Frontend", "fail", "Static files missing")
    except Exception as e:
        return CheckResult("Frontend", "fail", str(e)[:100])


async def check_websocket() -> CheckResult:
    """Check WebSocket availability."""
    try:
        from pathlib import Path
        ws_file = Path(__file__).parent / "web" / "routers" / "websocket.py"
        if ws_file.exists():
            return CheckResult("WebSocket", "ok", "WebSocket module present")
        else:
            return CheckResult("WebSocket", "fail", "WebSocket module missing")
    except Exception as e:
        return CheckResult("WebSocket", "fail", str(e)[:100])


def print_results(results: list[CheckResult]):
    """Print results in human-readable format."""
    print("\n" + "=" * 50)
    print("JARVIS Doctor Results")
    print("=" * 50 + "\n")
    
    icons = {"ok": "✓", "warn": "⚠", "fail": "✗"}
    colors = {"ok": "\033[92m", "warn": "\033[93m", "fail": "\033[91m"}
    reset = "\033[0m"
    
    for r in results:
        icon = icons.get(r.status, "?")
        color = colors.get(r.status, "")
        print(f"{color}{icon} {r.status.upper():6}{reset} {r.name}: {r.message}")
    
    print("\n" + "-" * 50)
    passed = sum(1 for r in results if r.status == "ok")
    warned = sum(1 for r in results if r.status == "warn")
    failed = sum(1 for r in results if r.status == "fail")
    print(f"Results: {passed} passed, {warned} warnings, {failed} failed\n")


async def main():
    """Main entry point."""
    results = await run_doctor()
    print_results(results)
    return 0 if all(r.status != "fail" for r in results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
