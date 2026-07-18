"""UIElement — Semantic representation of a UI element.

Every element on screen becomes a UIElement with:
  - type (button, menu, text_field, etc.)
  - name/label (what the user sees)
  - role (accessibility role)
  - state (enabled, focused, selected, etc.)
  - bounds (position and size)
  - children (nested elements)
  - app (which application owns it)

This is the foundation of semantic computer control.
"""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class ElementType(str, Enum):
    """Types of UI elements."""
    BUTTON = "button"
    MENU = "menu"
    MENU_ITEM = "menu_item"
    TEXT_FIELD = "text_field"
    TEXT_AREA = "text_area"
    CHECKBOX = "checkbox"
    RADIO_BUTTON = "radio_button"
    DROPDOWN = "dropdown"
    SLIDER = "slider"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    TAB = "tab"
    TOOLBAR = "toolbar"
    SCROLLBAR = "scrollbar"
    IMAGE = "image"
    LINK = "link"
    STATIC_TEXT = "static_text"
    GROUP = "group"
    WINDOW = "window"
    SHEET = "sheet"
    DIALOG = "dialog"
    POPUP = "popup"
    UNKNOWN = "unknown"


class ElementState(str, Enum):
    """State flags for UI elements."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    FOCUSED = "focused"
    SELECTED = "selected"
    CHECKED = "checked"
    UNCHECKED = "unchecked"
    EXPANDED = "expanded"
    COLLAPSED = "collapsed"
    HIDDEN = "hidden"
    MODAL = "modal"


@dataclass
class UIElement:
    """Semantic representation of a UI element.

    Every element on screen becomes a UIElement that JARVIS can
    understand and interact with using natural language.

    Example:
        element = UIElement(
            type=ElementType.BUTTON,
            name="Export",
            role="AXButton",
            states={ElementState.ENABLED},
        )
        if element.matches("export"):
            element.click()
    """
    # Identity
    id: str = ""
    name: str = ""              # Display name/label
    description: str = ""       # Accessibility description
    role: str = ""              # Raw accessibility role (AXButton, etc.)

    # Type
    type: str = ElementType.UNKNOWN
    sub_type: str = ""          # e.g., "submit" for buttons

    # State
    states: set = field(default_factory=set)

    # Position
    bounds: dict = field(default_factory=dict)  # {x, y, width, height}

    # Context
    app: str = ""               # Application name
    window: str = ""            # Window title
    parent_id: str = ""         # Parent element ID
    children_ids: list = field(default_factory=list)

    # Value
    value: str = ""             # Current value (for text fields, checkboxes)
    placeholder: str = ""       # Placeholder text

    # Metadata
    depth: int = 0              # Nesting depth in tree
    index: int = 0              # Sibling index
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "type": self.type,
            "sub_type": self.sub_type,
            "states": list(self.states),
            "bounds": self.bounds,
            "app": self.app,
            "window": self.window,
            "value": self.value,
            "placeholder": self.placeholder,
            "depth": self.depth,
            "index": self.index,
            "child_count": len(self.children_ids),
        }

    def matches(self, query: str) -> bool:
        """Check if this element matches a natural language query.

        Examples:
            element.matches("Save")      → name match
            element.matches("button")    → type match
            element.matches("export")    → fuzzy name match
            element.matches("search")    → name/type match
        """
        query_lower = query.lower().strip()
        name_lower = self.name.lower()
        desc_lower = self.description.lower()
        type_lower = self.type.lower()

        # Exact name match
        if query_lower == name_lower:
            return True

        # Exact type match
        if query_lower == type_lower:
            return True

        # Substring in name
        if query_lower in name_lower:
            return True

        # Substring in description
        if query_lower in desc_lower:
            return True

        # Fuzzy: remove spaces and check
        query_no_space = query_lower.replace(" ", "")
        name_no_space = name_lower.replace(" ", "")
        if query_no_space in name_no_space:
            return True

        return False

    def is_clickable(self) -> bool:
        """Check if this element can be clicked."""
        clickable_types = {
            ElementType.BUTTON, ElementType.MENU_ITEM, ElementType.LINK,
            ElementType.CHECKBOX, ElementType.RADIO_BUTTON, ElementType.TAB,
            ElementType.LIST_ITEM, ElementType.TABLE_ROW, ElementType.TABLE_CELL,
        }
        if self.type in clickable_types:
            return ElementState.ENABLED in self.states or not self.states
        return False

    def is_typeable(self) -> bool:
        """Check if this element can receive text input."""
        typeable_types = {
            ElementType.TEXT_FIELD, ElementType.TEXT_AREA,
        }
        return self.type in typeable_types

    def has_bounds(self) -> bool:
        """Check if element has valid position data."""
        return bool(self.bounds) and self.bounds.get("width", 0) > 0

    def center(self) -> Optional[tuple]:
        """Get the center point of this element."""
        if not self.has_bounds():
            return None
        x = self.bounds.get("x", 0) + self.bounds.get("width", 0) // 2
        y = self.bounds.get("y", 0) + self.bounds.get("height", 0) // 2
        return (x, y)

    def summary(self) -> str:
        """Compact human-readable summary."""
        parts = [self.type]
        if self.name:
            parts.append(f'"{self.name}"')
        if self.states:
            parts.append(f"[{','.join(self.states)}]")
        if self.has_bounds():
            b = self.bounds
            parts.append(f"({b.get('x',0)},{b.get('y',0)} {b.get('width',0)}x{b.get('height',0)})")
        return " ".join(parts)
