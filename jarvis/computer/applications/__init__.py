"""Application profiles — common UI patterns for known applications.

Each profile describes:
  - Common buttons, menus, keyboard shortcuts
  - Typical workflows (save, export, open file, etc.)
  - Expected UI element patterns
  - How JARVIS should interact with this application

Profiles let JARVIS know what to expect before even inspecting the UI,
making interaction faster and more reliable.
"""

from typing import Optional
from .base import ApplicationProfile, app_registry

# Re-export for convenience
__all__ = ["app_registry", "get_profile", "list_profiles"]


def get_profile(app_name: str) -> Optional[ApplicationProfile]:
    """Get the application profile by name."""
    return app_registry.get(app_name)


def list_profiles() -> list:
    """List all registered application profile names."""
    return app_registry.list_apps()
