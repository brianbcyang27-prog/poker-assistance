"""Object Detector — finds specific UI elements in screenshots.

Works with VisionResult objects to locate buttons, menus,
text fields, and other interactive elements.
"""

import logging
from typing import Optional, List
from .providers.base import VisionResult, DetectedObject

log = logging.getLogger("jarvis.vision.detector")


class ObjectDetector:
    """Finds and locates UI elements in vision analysis results.

    Provides methods to search, filter, and rank detected objects
    by type, name, position, or confidence.

    Usage:
        detector = ObjectDetector(vision_result)
        button = detector.find_button("Export")
        all_buttons = detector.find_all(type="button")
        nearest = detector.nearest_to(x=500, y=300)
    """

    def __init__(self, result: VisionResult = None):
        self._result = result or VisionResult()

    def set_result(self, result: VisionResult):
        """Set the vision result to analyze."""
        self._result = result

    @property
    def objects(self) -> list:
        return self._result.objects

    def find(self, query: str) -> Optional[DetectedObject]:
        """Find the best matching object for a natural language query.

        Matches against type, name, description, and color.
        Returns highest-confidence match.
        """
        matches = self.find_all(query=query)
        if not matches:
            return None
        return max(matches, key=lambda o: o.confidence)

    def find_all(self, query: str = "", type: str = "", name: str = "") -> List[DetectedObject]:
        """Find all objects matching criteria.

        All parameters are optional filters.
        """
        results = self._result.objects

        if query:
            query_lower = query.lower()
            results = [
                o for o in results
                if query_lower in o.type.lower()
                or query_lower in o.name.lower()
                or query_lower in o.description.lower()
                or query_lower in o.color.lower()
            ]

        if type:
            results = [o for o in results if type.lower() in o.type.lower()]

        if name:
            results = [o for o in results if name.lower() in o.name.lower()]

        return results

    def find_buttons(self, name: str = "") -> List[DetectedObject]:
        """Find all buttons, optionally filtered by name."""
        return self.find_all(type="button", name=name)

    def find_menus(self, name: str = "") -> List[DetectedObject]:
        """Find all menus/menu items."""
        return self.find_all(type="menu", name=name)

    def find_text_fields(self, name: str = "") -> List[DetectedObject]:
        """Find all text input fields."""
        return self.find_all(type="text_field", name=name)

    def find_by_color(self, color: str) -> List[DetectedObject]:
        """Find objects by dominant color."""
        return [o for o in self._result.objects if color.lower() in o.color.lower()]

    def nearest_to(self, x: int, y: int) -> Optional[DetectedObject]:
        """Find the object closest to given coordinates."""
        if not self._result.objects:
            return None

        def distance(obj):
            dx = obj.x - x
            dy = obj.y - y
            return (dx * dx + dy * dy) ** 0.5

        return min(self._result.objects, key=distance)

    def highest_confidence(self, min_confidence: float = 0.5) -> List[DetectedObject]:
        """Get objects above a confidence threshold, sorted by confidence."""
        filtered = [
            o for o in self._result.objects
            if o.confidence >= min_confidence
        ]
        return sorted(filtered, key=lambda o: o.confidence, reverse=True)

    def interactive_elements(self) -> List[DetectedObject]:
        """Get all interactive UI elements (buttons, menus, fields, links)."""
        interactive_types = {"button", "menu", "menu_item", "text_field", "text_area",
                             "link", "checkbox", "radio_button", "tab", "dropdown"}
        return [
            o for o in self._result.objects
            if any(t in o.type.lower() for t in interactive_types)
        ]

    def summary(self) -> dict:
        """Get summary statistics of detected objects."""
        type_counts = {}
        for obj in self._result.objects:
            type_counts[obj.type] = type_counts.get(obj.type, 0) + 1

        confidences = [o.confidence for o in self._result.objects]

        return {
            "total": len(self._result.objects),
            "types": type_counts,
            "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
            "min_confidence": min(confidences) if confidences else 0,
            "max_confidence": max(confidences) if confidences else 0,
            "interactive": len(self.interactive_elements()),
        }
