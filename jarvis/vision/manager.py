"""VisionManager — JARVIS's unified vision interface.

The central manager that coordinates:
  - Screenshot capture
  - Vision model analysis
  - Object detection
  - Grounding (vision → action)
  - Vision memory

This is the main entry point for all vision operations.

Usage:
    from jarvis.vision import vision_manager
    result = await vision_manager.capture_and_analyze()
    element = await vision_manager.find_object("blue button")
    action = await vision_manager.locate_element("Export")
"""

import asyncio
import logging
import time
from typing import Optional

from .screenshot import ScreenCapture, CapturedScreenshot, ScreenRegion
from .analyzer import VisionAnalyzer, ScreenAnalysis
from .detector import ObjectDetector
from .grounding import GroundingEngine, GroundedAction
from .memory import VisionMemory, VisualWorkflow

log = logging.getLogger("jarvis.vision.manager")


class VisionManager:
    """Unified vision interface — JARVIS's eyes.

    Coordinates the full vision pipeline:
      1. Capture screenshot
      2. Analyze with vision model
      3. Detect objects
      4. Ground into actions
      5. Store in memory

    Also provides multi-perception fallback:
      Try accessibility first → fall back to vision
    """

    def __init__(self):
        self._capture = ScreenCapture()
        self._analyzer = VisionAnalyzer()
        self._detector = ObjectDetector()
        self._grounding = GroundingEngine()
        self._memory = VisionMemory()
        self._provider = None
        self._initialized = False
        self._last_analysis: Optional[ScreenAnalysis] = None
        self._last_screenshot: Optional[CapturedScreenshot] = None

    async def initialize(self) -> dict:
        """Initialize the vision system and load the provider."""
        if self._initialized:
            return {"ok": True}

        from .providers import get_vision_provider
        self._provider = get_vision_provider()

        if self._provider:
            init_result = await self._provider.initialize()
            self._analyzer.set_provider(self._provider)
            self._grounding.set_accessibility(True)
            self._initialized = True
            log.info("Vision system initialized: %s/%s",
                     self._provider.name, self._provider.model)
            return {"ok": True, "provider": self._provider.name,
                    "model": self._provider.model}

        self._initialized = True
        log.warning("Vision system initialized without provider")
        return {"ok": True, "provider": None, "model": None}

    async def shutdown(self):
        """Cleanup resources."""
        await self._capture.cleanup(max_age_seconds=0)

    # ── Capture Methods ──────────────────────────────────────

    async def capture(self, mode: str = "full") -> Optional[CapturedScreenshot]:
        """Capture a screenshot.

        Args:
            mode: "full", "window", or "region"

        Returns:
            CapturedScreenshot or None
        """
        if mode == "window":
            screenshot = await self._capture.active_window()
        elif mode == "region":
            screenshot = await self._capture.full_screen()
        else:
            screenshot = await self._capture.full_screen()

        if screenshot:
            self._last_screenshot = screenshot
        return screenshot

    async def capture_region(self, x: int, y: int, w: int, h: int) -> Optional[CapturedScreenshot]:
        """Capture a specific screen region."""
        region = ScreenRegion(x=x, y=y, width=w, height=h)
        screenshot = await self._capture.region(region)
        if screenshot:
            self._last_screenshot = screenshot
        return screenshot

    # ── Analysis Methods ─────────────────────────────────────

    async def analyze(self, screenshot: CapturedScreenshot = None) -> ScreenAnalysis:
        """Analyze a screenshot.

        Args:
            screenshot: Screenshot to analyze (uses last captured if None)

        Returns:
            ScreenAnalysis with detected objects and description
        """
        if not screenshot:
            screenshot = self._last_screenshot
        if not screenshot:
            return ScreenAnalysis(description="No screenshot available")

        analysis = await self._analyzer.analyze_screenshot(screenshot)
        self._last_analysis = analysis
        self._detector.set_result(analysis)

        # Record in memory
        self._memory.record_screenshot(screenshot, analysis)

        # Emit event
        await self._emit_event("vision.analyzed", {
            "application": analysis.application,
            "object_count": len(analysis.objects),
            "description": analysis.description[:200],
        })

        return analysis

    async def capture_and_analyze(self, mode: str = "full") -> ScreenAnalysis:
        """Capture and analyze in one step — the most common operation."""
        screenshot = await self.capture(mode)
        if not screenshot:
            return ScreenAnalysis(description="Screenshot capture failed")
        return await self.analyze(screenshot)

    async def quick_describe(self, screenshot: CapturedScreenshot = None) -> str:
        """Quick natural language description without full analysis."""
        if not screenshot:
            screenshot = self._last_screenshot
        if not screenshot:
            return "No screenshot available"
        return await self._analyzer.quick_describe(screenshot)

    # ── Object Finding ───────────────────────────────────────

    async def find_object(self, query: str) -> Optional[dict]:
        """Find a UI object by natural language query.

        Returns the best matching detected object as a dict,
        or None if not found.
        """
        if not self._last_analysis:
            await self.capture_and_analyze()

        obj = self._detector.find(query)
        if obj:
            return obj.to_dict()
        return None

    async def find_all_objects(self, query: str) -> list:
        """Find all objects matching a query."""
        if not self._last_analysis:
            await self.capture_and_analyze()

        return [o.to_dict() for o in self._detector.find_all(query)]

    async def locate_element(self, query: str) -> GroundedAction:
        """Locate an element and return a grounded action.

        Tries:
          1. Accessibility first (if available)
          2. Vision detection (if available)

        Returns GroundedAction with the best method.
        """
        # Try accessibility first
        element = None
        try:
            from ..computer.accessibility import accessibility_manager
            await accessibility_manager.initialize()
            element = await accessibility_manager.find(query)
        except Exception:
            pass

        # Get vision results
        detected = []
        if self._last_analysis:
            detected = self._last_analysis.objects
        else:
            await self.capture_and_analyze()
            if self._last_analysis:
                detected = self._last_analysis.objects

        # Ground the action
        return self._grounding.ground_click(query, detected, element)

    async def locate_for_type(self, query: str, text: str) -> GroundedAction:
        """Locate a text field and return a grounded type action."""
        element = None
        try:
            from ..computer.accessibility import accessibility_manager
            await accessibility_manager.initialize()
            element = await accessibility_manager.find(query)
        except Exception:
            pass

        detected = []
        if self._last_analysis:
            detected = self._last_analysis.objects

        return self._grounding.ground_type(query, text, detected, element)

    # ── Memory Methods ───────────────────────────────────────

    def get_cached_location(self, app: str, element_name: str) -> Optional[dict]:
        """Get a cached element location from previous analysis."""
        return self._memory.find_cached_location(app, element_name)

    def save_workflow(self, workflow: VisualWorkflow):
        """Save a visual workflow."""
        self._memory.save_workflow(workflow)

    def get_workflow(self, workflow_id: str) -> Optional[VisualWorkflow]:
        """Get a workflow by ID."""
        return self._memory.get_workflow(workflow_id)

    def record_step(self, workflow_id: str, step: dict):
        """Record a step in a workflow."""
        self._memory.record_workflow_step(workflow_id, step)

    def complete_workflow(self, workflow_id: str, success: bool):
        """Mark a workflow as completed."""
        self._memory.complete_workflow(workflow_id, success)

    # ── Utility Methods ──────────────────────────────────────

    def get_detector(self) -> ObjectDetector:
        """Get the object detector for advanced queries."""
        return self._detector

    def get_memory(self) -> VisionMemory:
        """Get the vision memory."""
        return self._memory

    async def health_check(self) -> dict:
        """Check vision system health."""
        if self._provider:
            return await self._provider.health_check()
        return {"ok": False, "error": "No vision provider configured"}

    def get_stats(self) -> dict:
        """Get vision system statistics."""
        stats = {
            "initialized": self._initialized,
            "provider": self._provider.name if self._provider else None,
            "model": self._provider.model if self._provider else None,
            "last_analysis": self._last_analysis.to_dict() if self._last_analysis else None,
            "memory": self._memory.get_stats(),
        }
        return stats

    async def _emit_event(self, event_type: str, data: dict):
        """Emit a vision event."""
        try:
            from ..core.events import event_bus, Event
            await event_bus.emit(Event(
                type=event_type,
                data=data,
                source="vision",
            ))
        except Exception:
            pass


# Module-level singleton
vision_manager = VisionManager()
