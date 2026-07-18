"""Vision system — JARVIS's Eyes.

v4.5.0: Computer vision and visual understanding.

Architecture:
    Screenshot → Vision Provider → Analyzer → Detector → Grounding → Action

Priority order:
    1. Accessibility Tree (fast, structured)
    2. DOM / Application API (when available)
    3. Vision Model (fallback, multimodal)

Usage:
    from jarvis.vision import vision_manager
    result = await vision_manager.capture_and_analyze()
    element = await vision_manager.find_object("blue button")
    action = await vision_manager.locate_element("Export")
"""

from .screenshot import ScreenCapture, ScreenRegion
from .providers.base import VisionProvider, VisionResult, DetectedObject
from .providers import get_vision_provider
from .analyzer import VisionAnalyzer, ScreenAnalysis
from .detector import ObjectDetector
from .grounding import GroundingEngine, GroundedAction
from .memory import VisionMemory, VisualWorkflow
from .manager import VisionManager, vision_manager

__all__ = [
    # Screenshot
    "ScreenCapture", "ScreenRegion",
    # Provider
    "VisionProvider", "VisionResult", "DetectedObject", "get_vision_provider",
    # Analyzer
    "VisionAnalyzer", "ScreenAnalysis",
    # Detector
    "ObjectDetector",
    # Grounding
    "GroundingEngine", "GroundedAction",
    # Memory
    "VisionMemory", "VisualWorkflow",
    # Manager
    "VisionManager", "vision_manager",
]
