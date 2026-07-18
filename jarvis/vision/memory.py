"""Vision Memory — stores screenshots and visual workflows.

Remembers:
  - Screenshot history with analysis
  - Visual workflows (step-by-step UI interaction patterns)
  - Object location caches for frequently used apps
"""

import time
import json
import logging
from typing import Optional, List
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.vision.memory")


@dataclass
class VisualWorkflow:
    """A step-by-step visual workflow."""
    id: str = ""
    name: str = ""
    description: str = ""
    application: str = ""
    steps: list = field(default_factory=list)
    # Each step: {"description": str, "action": str, "target": str, "screenshot_id": str}
    success_count: int = 0
    fail_count: int = 0
    last_used: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "application": self.application,
            "steps": self.steps,
            "step_count": len(self.steps),
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "last_used": self.last_used,
            "created_at": self.created_at,
        }

    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.0


@dataclass
class ScreenshotRecord:
    """Record of a captured screenshot with analysis."""
    id: str = ""
    path: str = ""
    application: str = ""
    description: str = ""
    analysis: dict = field(default_factory=dict)
    task_id: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "application": self.application,
            "description": self.description,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
        }


class VisionMemory:
    """Stores visual context for JARVIS.

    Maintains:
      - In-memory screenshot history (last N captures)
      - Visual workflows (UI interaction patterns)
      - Object location cache (per application)

    Optionally persists to database.
    """

    def __init__(self, max_history: int = 100):
        self._screenshots: List[ScreenshotRecord] = []
        self._workflows: dict[str, VisualWorkflow] = {}
        self._object_cache: dict[str, dict] = {}  # app -> {name -> {x, y, type, last_seen}}
        self._max_history = max_history

    def record_screenshot(self, screenshot, analysis=None) -> ScreenshotRecord:
        """Record a screenshot with optional analysis."""
        record = ScreenshotRecord(
            id=screenshot.id if screenshot else "",
            path=screenshot.path if screenshot else "",
            application=screenshot.application if screenshot else "",
            description=analysis.description if analysis else "",
            analysis=analysis.to_dict() if analysis else {},
        )
        self._screenshots.append(record)

        # Trim history
        if len(self._screenshots) > self._max_history:
            self._screenshots = self._screenshots[-self._max_history:]

        # Update object cache
        if analysis and analysis.objects:
            app = record.application.lower()
            if app not in self._object_cache:
                self._object_cache[app] = {}
            for obj in analysis.objects:
                if obj.name:
                    self._object_cache[app][obj.name.lower()] = {
                        "x": obj.x, "y": obj.y,
                        "type": obj.type, "name": obj.name,
                        "last_seen": time.time(),
                    }

        return record

    def get_recent_screenshots(self, limit: int = 10) -> List[ScreenshotRecord]:
        """Get recent screenshot records."""
        return self._screenshots[-limit:]

    def find_cached_location(self, app: str, element_name: str) -> Optional[dict]:
        """Find a cached element location from previous analysis.

        Returns {"x": int, "y": int, "type": str} or None.
        """
        cache = self._object_cache.get(app.lower(), {})
        return cache.get(element_name.lower())

    def save_workflow(self, workflow: VisualWorkflow):
        """Save a visual workflow."""
        self._workflows[workflow.id] = workflow

    def get_workflow(self, workflow_id: str) -> Optional[VisualWorkflow]:
        """Get a visual workflow by ID."""
        return self._workflows.get(workflow_id)

    def find_workflows(self, app: str = "", query: str = "") -> List[VisualWorkflow]:
        """Find workflows by application or query."""
        results = list(self._workflows.values())
        if app:
            results = [w for w in results if w.application.lower() == app.lower()]
        if query:
            query_lower = query.lower()
            results = [
                w for w in results
                if query_lower in w.name.lower()
                or query_lower in w.description.lower()
            ]
        return results

    def record_workflow_step(self, workflow_id: str, step: dict):
        """Add a step to an existing workflow."""
        wf = self._workflows.get(workflow_id)
        if wf:
            wf.steps.append(step)

    def complete_workflow(self, workflow_id: str, success: bool):
        """Mark a workflow as completed."""
        wf = self._workflows.get(workflow_id)
        if wf:
            if success:
                wf.success_count += 1
            else:
                wf.fail_count += 1
            wf.last_used = time.time()

    def get_stats(self) -> dict:
        """Get memory statistics."""
        apps = set(s.application for s in self._screenshots if s.application)
        return {
            "screenshots": len(self._screenshots),
            "workflows": len(self._workflows),
            "cached_apps": list(self._object_cache.keys()),
            "unique_apps": list(apps),
        }

    def clear(self):
        """Clear all memory."""
        self._screenshots.clear()
        self._workflows.clear()
        self._object_cache.clear()
