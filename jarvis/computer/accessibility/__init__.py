"""Accessibility system — JARVIS's Eyes.

v4.4.0: Semantic computer control through UI element inspection.

Priority order for understanding applications:
  1. Accessibility Tree (fast, structured, no vision needed)
  2. Application APIs (when available)
  3. DOM inspection (for web content)
  4. Vision fallback (future v4.5)

Usage:
    from jarvis.computer.accessibility import accessibility_manager
    tree = await accessibility_manager.get_tree()
    elements = tree.find_elements(role="button")
    element = tree.find("Save")
"""

from .element import UIElement, ElementType, ElementState
from .tree import AccessibilityTree
from .base import AccessibilityProvider
from .manager import AccessibilityManager, accessibility_manager

__all__ = [
    "UIElement",
    "ElementType",
    "ElementState",
    "AccessibilityTree",
    "AccessibilityProvider",
    "AccessibilityManager",
    "accessibility_manager",
]
