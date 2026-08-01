"""
JARVIS Architecture System - Pluggable AI Agent Architectures
"""

from .base import AgentArchitecture, ArchitectureRegistry
from .hermes import HermesArchitecture
from .native import JarvisNativeArchitecture
from .settings import ArchitectureSettings, ArchitectureSettingsManager, get_settings_manager

__all__ = [
    "AgentArchitecture",
    "ArchitectureRegistry",
    "ArchitectureSettings",
    "ArchitectureSettingsManager",
    "JarvisNativeArchitecture",
    "HermesArchitecture",
    "get_architecture",
    "set_architecture",
    "list_architectures",
    "get_settings_manager",
]

# Global registry instance
_registry = ArchitectureRegistry()


def get_architecture(name: str = None) -> AgentArchitecture:
    """Get an architecture by name, or the default one."""
    return _registry.get(name)


def set_architecture(name: str) -> bool:
    """Set the default architecture."""
    return _registry.set_default(name)


def list_architectures() -> list:
    """List all available architectures."""
    return _registry.list()
