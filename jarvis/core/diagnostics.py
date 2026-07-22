"""JARVIS Startup Diagnostics — Self-Debug & Auto-Recovery.

Runs on server startup to verify all subsystems are healthy.
Attempts auto-recovery for common failures.
"""

import os
import time
import asyncio
from typing import List, Tuple, Optional
from pathlib import Path

from .config import get_config
from .reliability import config as reliability_config


class DiagnosticResult:
    def __init__(self, name: str, ok: bool, message: str, recovered: bool = False):
        self.name = name
        self.ok = ok
        self.message = message
        self.recovered = recovered

    def __repr__(self):
        status = "✓" if self.ok else "✗"
        rec = " (recovered)" if self.recovered else ""
        return f"{status} {self.name}: {self.message}{rec}"


async def run_diagnostics() -> List[DiagnosticResult]:
    """Run all system checks and attempt auto-recovery."""
    results: List[DiagnosticResult] = []

    # 1. Check port availability
    results.append(await _check_port())

    # 2. Check database
    results.append(await _check_database())

    # 3. Check LLM API
    results.append(await _check_llm())

    # 4. Check agent hierarchy
    results.append(await _check_agents())

    # 5. Check disk space
    results.append(await _check_disk())

    # 6. Check NVIDIA API key
    results.append(await _check_api_key())

    return results


async def _check_port() -> DiagnosticResult:
    """Check if the configured port is available."""
    config = get_config()
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", config.port))
        if result == 0:
            return DiagnosticResult("port", True, f"Port {config.port} is serving (this server)")
        return DiagnosticResult("port", True, f"Port {config.port} is available")
    finally:
        sock.close()


async def _kill_zombie_on_port(port: int) -> bool:
    """Kill any process holding the given port. Returns True if killed."""
    try:
        import subprocess
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                pid = pid.strip()
                if pid:
                    subprocess.run(["kill", "-9", pid], capture_output=True, timeout=5)
            await asyncio.sleep(1)
            return True
    except Exception:
        pass
    return False


async def _check_database() -> DiagnosticResult:
    """Check database connectivity and recover from WAL locks."""
    try:
        from .database import get_db
        db = await get_db()
        # Use the raw aiosqlite connection for the health check
        if db._db is None:
            return DiagnosticResult("database", False, "Database not connected")
        cursor = await db._db.execute("SELECT 1")
        await cursor.fetchone()
        return DiagnosticResult("database", True, "SQLite database responsive")
    except Exception as e:
        error_msg = str(e).lower()
        if "locked" in error_msg or "busy" in error_msg:
            recovered = await _recover_database_lock()
            if recovered:
                return DiagnosticResult("database", True, "Database was locked — recovered", recovered=True)
        return DiagnosticResult("database", False, f"Database error: {e}")


async def _recover_database_lock() -> bool:
    """Recover from SQLite WAL lock by removing stale SHM/WAL files.
    
    Safety: Only deletes files if no active database connection exists.
    """
    try:
        from .database import get_db, _db
        # Don't delete if there's an active connection
        if _db and _db._db:
            return False
        
        config = get_config()
        db_path = Path(config.db_path)
        for suffix in ["-shm", "-wal"]:
            lock_file = db_path.parent / f"{db_path.name}{suffix}"
            if lock_file.exists():
                lock_file.unlink()
        return True
    except Exception:
        return False


async def _check_llm() -> DiagnosticResult:
    """Check LLM API availability."""
    try:
        from ..brain.llm import LLM
        llm = LLM()
        if not llm.is_available():
            return DiagnosticResult("llm", False, "No LLM backend available — set NVIDIA_API_KEY or install Ollama")

        # Quick health check: send a minimal request
        base_url, api_key, model = llm._get_endpoint()
        url = f"{base_url}/models"
        import httpx
        async with httpx.AsyncClient(timeout=reliability_config.health_check_timeout) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            if resp.status_code == 200:
                return DiagnosticResult("llm", True, f"LLM API reachable ({model})")
            elif resp.status_code == 401:
                return DiagnosticResult("llm", False, "LLM API key is invalid")
            else:
                return DiagnosticResult("llm", False, f"LLM API returned {resp.status_code}")
    except Exception as e:
        return DiagnosticResult("llm", False, f"LLM check failed: {e}")


async def _check_agents() -> DiagnosticResult:
    """Check agent hierarchy integrity by examining registered workers."""
    try:
        from ..agents.kings import EngineeringKing, PersonalKing, ResearchKing, SystemKing
        kings = [EngineeringKing(), PersonalKing(), ResearchKing(), SystemKing()]
        total_workers = sum(len(k.get_all_workers()) for k in kings)

        if total_workers < 20:
            return DiagnosticResult("agents", False, f"Only {total_workers}/23 workers registered")

        return DiagnosticResult("agents", True, f"4 kings, {total_workers} workers")
    except Exception as e:
        return DiagnosticResult("agents", False, f"Agent check failed: {e}")


async def _check_disk() -> DiagnosticResult:
    """Check available disk space."""
    try:
        stat = os.statvfs("/")
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        if free_gb < 1.0:
            return DiagnosticResult("disk", False, f"Low disk space: {free_gb:.1f} GB free")
        return DiagnosticResult("disk", True, f"{free_gb:.1f} GB free")
    except Exception as e:
        return DiagnosticResult("disk", False, f"Disk check failed: {e}")


async def _check_api_key() -> DiagnosticResult:
    """Verify NVIDIA API key is configured."""
    config = get_config()
    if not config.nvidia_api_key:
        return DiagnosticResult("api_key", False, "NVIDIA_API_KEY not set in .env")
    if not config.nvidia_api_key.startswith("nvapi-"):
        return DiagnosticResult("api_key", False, "NVIDIA_API_KEY format invalid (expected nvapi-...)")
    return DiagnosticResult("api_key", True, "NVIDIA API key configured")
