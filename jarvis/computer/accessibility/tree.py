"""AccessibilityTree — Structured traversal and search of UI elements.

Wraps a flat list of UIElements into a searchable tree structure
with find, filter, and traversal methods.
"""

import logging
from typing import Optional
from .element import UIElement, ElementType

log = logging.getLogger("jarvis.computer.accessibility.tree")


class AccessibilityTree:
    """Structured view of a window's UI elements.

    Provides find, filter, and traversal methods over a flat list
    of UIElement objects. Maintains parent-child relationships.

    Usage:
        tree = AccessibilityTree(elements, app="Finder", window="Documents")
        buttons = tree.find_elements(role="button")
        save_btn = tree.find("Save")
        tree.print_tree()
    """

    def __init__(self, elements: list[UIElement] = None, app: str = "", window: str = ""):
        self.app = app
        self.window = window
        self._elements: list[UIElement] = []
        self._by_id: dict[str, UIElement] = {}
        self._by_name: dict[str, list[UIElement]] = {}
        self._by_type: dict[str, list[UIElement]] = {}

        if elements:
            for el in elements:
                self.add(el)

    def add(self, element: UIElement):
        """Add an element to the tree."""
        self._elements.append(element)
        if element.id:
            self._by_id[element.id] = element

        # Index by name
        name_key = element.name.lower().strip()
        if name_key:
            self._by_name.setdefault(name_key, []).append(element)

        # Index by type
        self._by_type.setdefault(element.type, []).append(element)

    def find(self, query: str) -> Optional[UIElement]:
        """Find the first element matching a natural language query.

        Tries in order:
          1. Exact name match
          2. Substring name match
          3. Type match
          4. Fuzzy match

        Examples:
            tree.find("Save")        → button named "Save"
            tree.find("button")      → first button
            tree.find("File menu")   → menu named "File"
        """
        query_lower = query.lower().strip()

        # Exact name match
        exact = self._by_name.get(query_lower, [])
        if exact:
            return exact[0]

        # Substring name match
        for name_key, elements in self._by_name.items():
            if query_lower in name_key or name_key in query_lower:
                return elements[0]

        # Type match
        type_match = self._by_type.get(query_lower, [])
        if type_match:
            return type_match[0]

        # Fuzzy match across all elements
        for el in self._elements:
            if el.matches(query):
                return el

        return None

    def find_elements(
        self,
        name: str = "",
        role: str = "",
        type: str = "",
        app: str = "",
        clickable_only: bool = False,
    ) -> list[UIElement]:
        """Find all elements matching criteria.

        All parameters are optional filters. Empty = no filter.
        """
        results = self._elements[:]

        if name:
            name_lower = name.lower()
            results = [el for el in results if name_lower in el.name.lower()]

        if role:
            role_lower = role.lower()
            results = [el for el in results if role_lower in el.role.lower()]

        if type:
            results = [el for el in results if el.type == type]

        if app:
            results = [el for el in results if el.app.lower() == app.lower()]

        if clickable_only:
            results = [el for el in results if el.is_clickable()]

        return results

    def find_all(self, query: str) -> list[UIElement]:
        """Find ALL elements matching a query (not just first)."""
        return [el for el in self._elements if el.matches(query)]

    def get_buttons(self) -> list[UIElement]:
        """Get all buttons."""
        return self._by_type.get(ElementType.BUTTON, [])

    def get_menus(self) -> list[UIElement]:
        """Get all menus."""
        return self._by_type.get(ElementType.MENU, []) + self._by_type.get(ElementType.MENU_ITEM, [])

    def get_text_fields(self) -> list[UIElement]:
        """Get all text input fields."""
        return self._by_type.get(ElementType.TEXT_FIELD, []) + self._by_type.get(ElementType.TEXT_AREA, [])

    def get_interactive(self) -> list[UIElement]:
        """Get all interactive elements (clickable + typeable)."""
        return [el for el in self._elements if el.is_clickable() or el.is_typeable()]

    @property
    def elements(self) -> list[UIElement]:
        return self._elements

    @property
    def element_count(self) -> int:
        return len(self._elements)

    def stats(self) -> dict:
        """Get summary statistics of the tree."""
        type_counts = {}
        for el in self._elements:
            type_counts[el.type] = type_counts.get(el.type, 0) + 1

        return {
            "total": len(self._elements),
            "app": self.app,
            "window": self.window,
            "types": type_counts,
            "buttons": len(self.get_buttons()),
            "menus": len(self.get_menus()),
            "text_fields": len(self.get_text_fields()),
            "interactive": len(self.get_interactive()),
        }

    def to_dict(self) -> dict:
        """Serialize tree to dict."""
        return {
            "app": self.app,
            "window": self.window,
            "element_count": len(self._elements),
            "stats": self.stats(),
            "elements": [el.to_dict() for el in self._elements[:100]],
        }

    def to_context(self, max_elements: int = 50) -> str:
        """Format as context string for LLM consumption.

        Returns a compact representation the LLM can use
        to understand the current UI state.
        """
        parts = []
        parts.append(f"Application: {self.app}")
        parts.append(f"Window: {self.window}")
        parts.append(f"Elements: {len(self._elements)}")
        parts.append("")

        # Group by type
        by_type = {}
        for el in self._elements[:max_elements]:
            by_type.setdefault(el.type, []).append(el)

        for elem_type, elements in by_type.items():
            parts.append(f"{elem_type.upper()}S ({len(elements)}):")
            for el in elements[:10]:
                parts.append(f"  - {el.summary()}")
            parts.append("")

        return "\n".join(parts)

    def print_tree(self, max_depth: int = 3):
        """Print a visual tree of elements."""
        lines = [f"=== {self.app} / {self.window} ({len(self._elements)} elements) ==="]
        for el in self._elements:
            if el.depth > max_depth:
                continue
            indent = "  " * el.depth
            lines.append(f"{indent}{el.summary()}")
        print("\n".join(lines))

    def __len__(self):
        return len(self._elements)

    def __iter__(self):
        return iter(self._elements)

    def __repr__(self):
        return f"AccessibilityTree(app={self.app!r}, window={self.window!r}, elements={len(self._elements)})"
