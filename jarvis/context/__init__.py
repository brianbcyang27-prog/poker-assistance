"""Context Engine - Tracks ALL current state and maintains a searchable timeline.

Monitors apps, files, git, browser, terminals, and system resources.
Persists timeline to JSON. All async, stdlib only.

Designed for Python 3.9.6+ with stdlib only.
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

from jarvis.context.models import ContextSummary, CurrentContext, TimelineEvent

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path.home() / ".jarvis" / "context"
TIMELINE_MAX = 1000
CATEGORIES = frozenset(
    ["app", "file", "git", "browser", "terminal", "mission", "device", "conversation", "system"]
)


def _get_cpu_memory() -> Dict[str, float]:
    """Get CPU and memory percentages. Tries psutil, falls back to stdlib."""
    try:
        import psutil  # type: ignore

        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
        }
    except ImportError:
        pass
    try:
        load = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        cpu_pct = (load[0] / cpu_count) * 100.0
        return {"cpu_percent": round(min(cpu_pct, 100.0), 1), "memory_percent": 0.0}
    except (OSError, AttributeError):
        return {"cpu_percent": 0.0, "memory_percent": 0.0}


def _git_info(repo_path: str = ".") -> Dict[str, str]:
    """Get current git branch and repo name (non-blocking)."""
    info: Dict[str, str] = {"branch": "", "repo": ""}
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        info["branch"] = result.stdout.strip()
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        toplevel = result.stdout.strip()
        if toplevel:
            info["repo"] = os.path.basename(toplevel)
    except Exception:
        pass
    return info


class ContextEngine:
    """Tracks current state and maintains a searchable timeline.

    All mutations are protected by an asyncio lock for thread safety.
    Timeline is stored in memory (deque) and persisted to a JSON file.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or DEFAULT_DATA_DIR
        self._timeline_file = self._data_dir / "timeline.json"
        self._context_file = self._data_dir / "context.json"
        self._lock = asyncio.Lock()
        self._timeline: deque = deque(maxlen=TIMELINE_MAX)
        self._categories: Dict[str, Dict[str, Any]] = {c: {} for c in CATEGORIES}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._start_time: Optional[float] = None

    async def start(self) -> None:
        """Begin monitoring. Loads persisted data."""
        async with self._lock:
            if self._running:
                return
            self._running = True
            self._start_time = time.time()
            self._data_dir.mkdir(parents=True, exist_ok=True)
            await self._load_timeline()
            await self._load_context()
            self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("ContextEngine started")

    async def stop(self) -> None:
        """Stop monitoring and persist data."""
        async with self._lock:
            self._running = False
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        await self.save()
        logger.info("ContextEngine stopped")

    async def _monitor_loop(self) -> None:
        """Periodically update system stats."""
        while self._running:
            try:
                stats = _get_cpu_memory()
                async with self._lock:
                    self._categories["system"] = {
                        **self._categories["system"],
                        **stats,
                        "last_update": time.time(),
                    }
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("ContextEngine monitor tick failed")
            await asyncio.sleep(10.0)

    async def get_current_context(self) -> CurrentContext:
        """Build full current state from all categories."""
        async with self._lock:
            ctx = CurrentContext()
            ctx.cpu_percent = self._categories.get("system", {}).get("cpu_percent", 0.0)
            ctx.memory_percent = self._categories.get("system", {}).get("memory_percent", 0.0)
            ctx.active_app = self._categories.get("app", {}).get("active", "")
            ctx.active_file = self._categories.get("file", {}).get("active", "")
            ctx.git_branch = self._categories.get("git", {}).get("branch", "")
            ctx.git_repo = self._categories.get("git", {}).get("repo", "")
            ctx.browser_tabs = list(self._categories.get("browser", {}).get("tabs", []))
            ctx.open_files = list(self._categories.get("file", {}).get("open", []))
            ctx.running_terminals = list(self._categories.get("terminal", {}).get("running", []))
            ctx.current_mission = self._categories.get("mission", {}).get("current", "")
            ctx.connected_devices = list(self._categories.get("device", {}).get("connected", []))
            ctx.recent_conversations = list(
                self._categories.get("conversation", {}).get("recent", [])
            )
            ctx.context_dict = dict(self._categories)
            if self._start_time is not None:
                ctx.uptime_seconds = time.time() - self._start_time
            return ctx

    async def update(self, category: str, data: Dict[str, Any]) -> None:
        """Update a context category."""
        if category not in CATEGORIES:
            logger.warning("Unknown context category: %s", category)
        async with self._lock:
            self._categories.setdefault(category, {}).update(data)

    async def add_timeline_event(self, event: TimelineEvent) -> None:
        """Add an event to the timeline."""
        async with self._lock:
            self._timeline.append(event)

    async def search_timeline(self, query: str, limit: int = 20) -> List[TimelineEvent]:
        """Search events by query string (case-insensitive substring match)."""
        query_lower = query.lower()
        results: List[TimelineEvent] = []
        async with self._lock:
            for event in reversed(self._timeline):
                if (
                    query_lower in event.detail.lower()
                    or query_lower in event.category.lower()
                    or query_lower in event.action.lower()
                ):
                    results.append(event)
                    if len(results) >= limit:
                        break
        return results

    async def get_timeline(self, hours: int = 24) -> List[TimelineEvent]:
        """Return events from the last N hours."""
        cutoff = time.time() - (hours * 3600)
        async with self._lock:
            return [e for e in self._timeline if e.timestamp >= cutoff]

    async def get_summary(self) -> ContextSummary:
        """Build a human-readable summary of current context."""
        ctx = await self.get_current_context()
        cutoff = time.time() - 86400  # last 24h
        today_count = 0
        recent_files: List[str] = []
        recent_commits: List[str] = []
        async with self._lock:
            for event in self._timeline:
                if event.timestamp >= cutoff:
                    today_count += 1
                    if event.category == "file" and event.detail not in recent_files:
                        recent_files.append(event.detail)
                    if event.category == "git" and event.detail not in recent_commits:
                        recent_commits.append(event.detail)
        return ContextSummary(
            active_project=ctx.git_repo or ctx.current_project,
            today_events_count=today_count,
            active_apps=[ctx.active_app] if ctx.active_app else [],
            recent_files=recent_files[:10],
            recent_commits=recent_commits[:10],
            current_focus=ctx.current_mission or ctx.active_app,
        )

    async def save(self) -> None:
        """Persist timeline and context to JSON files."""
        async with self._lock:
            timeline_data = [
                {
                    "id": e.id,
                    "timestamp": e.timestamp,
                    "category": e.category,
                    "action": e.action,
                    "detail": e.detail,
                    "metadata": e.metadata,
                }
                for e in self._timeline
            ]
            context_data = dict(self._categories)
        try:
            self._timeline_file.write_text(json.dumps(timeline_data, indent=2))
            self._context_file.write_text(json.dumps(context_data, indent=2))
        except OSError:
            logger.exception("Failed to persist context data")

    async def load(self) -> None:
        """Load persisted data from disk."""
        await self._load_timeline()
        await self._load_context()

    async def _load_timeline(self) -> None:
        """Load timeline from JSON file."""
        if not self._timeline_file.exists():
            return
        try:
            data = json.loads(self._timeline_file.read_text())
            async with self._lock:
                for item in data:
                    self._timeline.append(
                        TimelineEvent(
                            id=item.get("id", ""),
                            timestamp=item.get("timestamp", 0.0),
                            category=item.get("category", "system"),
                            action=item.get("action", "observed"),
                            detail=item.get("detail", ""),
                            metadata=item.get("metadata", {}),
                        )
                    )
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load timeline")

    async def _load_context(self) -> None:
        """Load context categories from JSON file."""
        if not self._context_file.exists():
            return
        try:
            data = json.loads(self._context_file.read_text())
            async with self._lock:
                for category, values in data.items():
                    if isinstance(values, dict):
                        self._categories.setdefault(category, {}).update(values)
        except (json.JSONDecodeError, OSError):
            logger.exception("Failed to load context")

    def get_stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        uptime = 0.0
        if self._start_time is not None:
            uptime = time.time() - self._start_time
        return {
            "running": self._running,
            "timeline_size": len(self._timeline),
            "timeline_max": TIMELINE_MAX,
            "categories": list(self._categories.keys()),
            "uptime_seconds": round(uptime, 1),
            "data_dir": str(self._data_dir),
        }
