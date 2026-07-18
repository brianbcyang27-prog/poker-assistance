"""Application profile base — describes known application UI patterns.

Each profile tells JARVIS:
  - What buttons/menus to expect
  - How to perform common workflows
  - What keyboard shortcuts are available
  - What UI elements are typically present
"""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class ApplicationProfile:
    """Description of a known application's UI patterns."""

    name: str                           # Display name
    bundle_id: str = ""                 # macOS bundle ID (e.g., com.apple.finder)
    executable: str = ""                # Process name (e.g., "Finder")
    category: str = "general"           # Category (browser, cad, editor, file_manager, terminal, etc.)

    # Common UI elements
    common_buttons: list[str] = field(default_factory=list)    # ["Save", "Cancel", "Open", ...]
    common_menus: list[str] = field(default_factory=list)      # ["File", "Edit", "View", ...]
    common_shortcuts: dict[str, str] = field(default_factory=dict)  # {"save": "Cmd+S", ...}

    # Workflows
    workflows: dict[str, list[str]] = field(default_factory=dict)
    # {"save": ["File menu", "Save"], "export": ["File menu", "Export..."]}

    # How JARVIS should interact
    interaction_notes: str = ""         # Free-text notes for the LLM

    def describe(self) -> str:
        """Compact description for LLM context."""
        parts = [f"Application: {self.name}"]
        if self.category:
            parts.append(f"Category: {self.category}")
        if self.common_buttons:
            parts.append(f"Common buttons: {', '.join(self.common_buttons[:10])}")
        if self.common_menus:
            parts.append(f"Menus: {', '.join(self.common_menus[:8])}")
        if self.common_shortcuts:
            shortcuts = ", ".join(f"{k}: {v}" for k, v in list(self.common_shortcuts.items())[:6])
            parts.append(f"Shortcuts: {shortcuts}")
        if self.workflows:
            parts.append(f"Workflows: {', '.join(self.workflows.keys())}")
        if self.interaction_notes:
            parts.append(f"Notes: {self.interaction_notes}")
        return "\n".join(parts)


class ApplicationRegistry:
    """Registry of known application profiles."""

    def __init__(self):
        self._profiles: dict[str, ApplicationProfile] = {}

    def register(self, profile: ApplicationProfile):
        """Register an application profile."""
        self._profiles[profile.name.lower()] = profile

    def get(self, app_name: str) -> Optional[ApplicationProfile]:
        """Get a profile by name (case-insensitive)."""
        return self._profiles.get(app_name.lower())

    def list_apps(self) -> list[str]:
        """List all registered app names."""
        return sorted(self._profiles.keys())

    def find_by_bundle(self, bundle_id: str) -> Optional[ApplicationProfile]:
        """Find a profile by macOS bundle ID."""
        for profile in self._profiles.values():
            if profile.bundle_id == bundle_id:
                return profile
        return None

    def find_by_executable(self, exe: str) -> Optional[ApplicationProfile]:
        """Find a profile by executable name."""
        exe_lower = exe.lower()
        for profile in self._profiles.values():
            if profile.executable.lower() == exe_lower:
                return profile
        return None

    def describe_all(self) -> str:
        """Describe all registered applications."""
        return "\n\n".join(p.describe() for p in self._profiles.values())


# Global registry
app_registry = ApplicationRegistry()
