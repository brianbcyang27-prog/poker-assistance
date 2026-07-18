"""Vision Analyzer — understands what's on screen.

Combines screenshot capture with vision model analysis
to produce structured understanding of the screen state.
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

from .providers.base import VisionResult, DetectedObject

log = logging.getLogger("jarvis.vision.analyzer")


@dataclass
class ScreenAnalysis:
    """Complete analysis of a screen capture."""
    application: str = ""
    description: str = ""
    objects: list = field(default_factory=list)
    buttons: list = field(default_factory=list)
    menus: list = field(default_factory=list)
    text_fields: list = field(default_factory=list)
    text_content: str = ""
    layout: dict = field(default_factory=dict)
    screenshot_id: str = ""
    screenshot_path: str = ""
    provider: str = ""
    model: str = ""
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "application": self.application,
            "description": self.description,
            "object_count": len(self.objects),
            "buttons": [o.to_dict() for o in self.buttons],
            "menus": [o.to_dict() for o in self.menus],
            "text_fields": [o.to_dict() for o in self.text_fields],
            "text_content": self.text_content,
            "layout": self.layout,
            "screenshot_id": self.screenshot_id,
            "provider": self.provider,
            "model": self.model,
            "duration_ms": round(self.duration_ms, 2),
        }

    def to_context(self) -> str:
        """Format as context string for LLM consumption."""
        parts = []
        parts.append(f"Screen: {self.application or 'Unknown'}")
        parts.append(f"Description: {self.description}")
        parts.append(f"Objects detected: {len(self.objects)}")
        if self.buttons:
            parts.append(f"Buttons: {', '.join(b.name or b.type for b in self.buttons[:10])}")
        if self.menus:
            parts.append(f"Menus: {', '.join(m.name or m.type for m in self.menus[:10])}")
        if self.text_fields:
            parts.append(f"Text fields: {len(self.text_fields)}")
        if self.text_content:
            parts.append(f"Visible text: {self.text_content[:200]}")
        return "\n".join(parts)


class VisionAnalyzer:
    """Analyzes screenshots to understand what's on screen.

    Combines:
      - Screenshot capture
      - Vision model analysis
      - Object classification
      - Layout understanding

    Usage:
        analyzer = VisionAnalyzer(provider)
        analysis = await analyzer.analyze_screenshot(screenshot)
    """

    def __init__(self, provider=None):
        self._provider = provider

    def set_provider(self, provider):
        """Set the vision provider."""
        self._provider = provider

    async def analyze_screenshot(self, screenshot) -> ScreenAnalysis:
        """Analyze a captured screenshot.

        Args:
            screenshot: CapturedScreenshot from ScreenCapture

        Returns:
            ScreenAnalysis with classified objects and description
        """
        if not self._provider:
            return ScreenAnalysis(
                description="No vision provider configured",
                screenshot_id=screenshot.id if screenshot else "",
                screenshot_path=screenshot.path if screenshot else "",
            )

        result = await self._provider.analyze_image(image_path=screenshot.path)
        return self._build_analysis(result, screenshot)

    async def analyze_path(self, image_path: str) -> ScreenAnalysis:
        """Analyze an image file directly."""
        if not self._provider:
            return ScreenAnalysis(description="No vision provider configured")

        result = await self._provider.analyze_image(image_path=image_path)
        return self._build_analysis(result)

    async def quick_describe(self, screenshot) -> str:
        """Quick natural language description of a screenshot."""
        if not self._provider:
            return "No vision provider configured"
        return await self._provider.describe_screen(image_path=screenshot.path)

    def _build_analysis(self, result: VisionResult, screenshot=None) -> ScreenAnalysis:
        """Build ScreenAnalysis from VisionResult."""
        analysis = ScreenAnalysis(
            application=result.application,
            description=result.screen_description,
            objects=result.objects,
            text_content=result.text_content,
            layout=result.layout,
            provider=result.provider,
            model=result.model,
            duration_ms=result.duration_ms,
        )

        if screenshot:
            analysis.screenshot_id = screenshot.id
            analysis.screenshot_path = screenshot.path

        # Classify objects by type
        for obj in result.objects:
            obj_type = obj.type.lower()
            if "button" in obj_type or "btn" in obj_type:
                analysis.buttons.append(obj)
            elif "menu" in obj_type or "menubar" in obj_type:
                analysis.menus.append(obj)
            elif "text" in obj_type or "field" in obj_type or "input" in obj_type:
                analysis.text_fields.append(obj)

        return analysis
