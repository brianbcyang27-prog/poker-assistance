"""Grounding Engine — converts visual understanding into actions.

Takes detected objects and converts them into actionable commands
that ComputerManager can execute.

Flow:
    Vision says: Button "Export" at x=500, y=200
    Grounding converts: computer.click(500, 200)
                       or accessibility.click("Export")
"""

import logging
from typing import Optional
from dataclasses import dataclass

from .providers.base import DetectedObject

log = logging.getLogger("jarvis.vision.grounding")


@dataclass
class GroundedAction:
    """An action grounded in visual understanding."""
    action_type: str = ""     # click, type_into, double_click, right_click
    method: str = ""          # vision, accessibility, hybrid
    x: int = 0               # target coordinates
    y: int = 0
    element_name: str = ""    # semantic name
    element_type: str = ""    # button, menu, text_field, etc.
    text: str = ""            # text to type (for type actions)
    confidence: float = 0.0   # grounding confidence
    reasoning: str = ""       # why this action was chosen

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "method": self.method,
            "x": self.x,
            "y": self.y,
            "element_name": self.element_name,
            "element_type": self.element_type,
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
        }


class GroundingEngine:
    """Converts visual detections into actionable commands.

    Decides the best method for each action:
      1. If accessibility can find the element → use accessibility
      2. If vision found it with good coordinates → use vision click
      3. If hybrid needed → combine both

    Usage:
        engine = GroundingEngine()
        action = engine.ground_click("Export", detected_objects)
        # Returns GroundedAction with accessibility or vision method
    """

    def __init__(self):
        self._accessibility_available = False

    def set_accessibility(self, available: bool):
        """Set whether accessibility is available."""
        self._accessibility_available = available

    def ground_click(
        self,
        query: str,
        detected_objects: list = None,
        element: object = None,
    ) -> GroundedAction:
        """Ground a click action.

        Args:
            query: What to click ("Export", "Save button", etc.)
            detected_objects: Vision-detected objects
            element: Accessibility element if found

        Returns:
            GroundedAction with the best method
        """
        # Prefer accessibility if element is available
        if element and hasattr(element, 'name'):
            if element.has_bounds() if hasattr(element, 'has_bounds') else True:
                center = element.center() if hasattr(element, 'center') else None
                return GroundedAction(
                    action_type="click",
                    method="accessibility",
                    x=center[0] if center else 0,
                    y=center[1] if center else 0,
                    element_name=getattr(element, 'name', query),
                    element_type=getattr(element, 'type', 'unknown'),
                    confidence=0.95,
                    reasoning=f"Accessibility found element '{element.name}'",
                )

        # Fall back to vision detection
        if detected_objects:
            best = self._find_best_match(query, detected_objects)
            if best and best.confidence >= 0.5:
                return GroundedAction(
                    action_type="click",
                    method="vision",
                    x=best.x,
                    y=best.y,
                    element_name=best.name or query,
                    element_type=best.type,
                    confidence=best.confidence,
                    reasoning=f"Vision detected '{best.name}' ({best.type}) "
                              f"at ({best.x},{best.y}) with confidence {best.confidence:.2f}",
                )

        # No detection — return with low confidence
        return GroundedAction(
            action_type="click",
            method="unknown",
            element_name=query,
            confidence=0.0,
            reasoning=f"Could not ground '{query}' — no matching element found",
        )

    def ground_type(
        self,
        query: str,
        text: str,
        detected_objects: list = None,
        element: object = None,
    ) -> GroundedAction:
        """Ground a type-into action."""
        if element and hasattr(element, 'name'):
            center = element.center() if hasattr(element, 'center') else None
            return GroundedAction(
                action_type="type_into",
                method="accessibility",
                x=center[0] if center else 0,
                y=center[1] if center else 0,
                element_name=getattr(element, 'name', query),
                element_type=getattr(element, 'type', 'text_field'),
                text=text,
                confidence=0.95,
                reasoning=f"Accessibility found text field '{element.name}'",
            )

        if detected_objects:
            text_fields = [
                o for o in detected_objects
                if "text" in o.type.lower() or "field" in o.type.lower() or "input" in o.type.lower()
            ]
            best = self._find_best_match(query, text_fields or detected_objects)
            if best and best.confidence >= 0.5:
                return GroundedAction(
                    action_type="type_into",
                    method="vision",
                    x=best.x,
                    y=best.y,
                    element_name=best.name or query,
                    element_type=best.type,
                    text=text,
                    confidence=best.confidence,
                    reasoning=f"Vision detected text field '{best.name}' at ({best.x},{best.y})",
                )

        return GroundedAction(
            action_type="type_into",
            method="unknown",
            element_name=query,
            text=text,
            confidence=0.0,
            reasoning=f"Could not ground type action for '{query}'",
        )

    def _find_best_match(self, query: str, objects: list) -> Optional[DetectedObject]:
        """Find the best matching object for a query."""
        query_lower = query.lower()
        scored = []

        for obj in objects:
            score = 0.0
            name_lower = obj.name.lower()
            type_lower = obj.type.lower()

            # Exact name match
            if query_lower == name_lower:
                score = 1.0
            # Substring match
            elif query_lower in name_lower:
                score = 0.8
            elif name_lower in query_lower:
                score = 0.7
            # Type match
            elif query_lower in type_lower:
                score = 0.5
            # Fuzzy
            elif any(word in name_lower for word in query_lower.split()):
                score = 0.6

            if score > 0:
                scored.append((score * obj.confidence, obj))

        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[0][1]

        return None
