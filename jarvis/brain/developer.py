"""Developer Mode — Debug endpoints, feature flags, and internal state inspection.

Provides runtime introspection, feature toggles, and debug utilities
for development and troubleshooting.
"""

import os
import time
import sys
from dataclasses import dataclass, field
from typing import Any, Optional
from loguru import logger


@dataclass
class FeatureFlag:
    """A feature flag with toggle capability."""
    name: str
    enabled: bool = True
    description: str = ""
    created_at: float = field(default_factory=time.time)
    toggled_at: float = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "description": self.description,
            "created_at": self.created_at,
            "toggled_at": self.toggled_at,
        }


class DeveloperMode:
    """Runtime debugging and feature flag management."""

    def __init__(self):
        self._flags: dict[str, FeatureFlag] = {}
        self._debug_data: dict[str, Any] = {}
        self._enabled = os.getenv("JARVIS_DEV_MODE", "0") == "1"
        self._init_default_flags()

    def _init_default_flags(self):
        """Initialize default feature flags."""
        defaults = [
            ("rag_memory", True, "Enable RAG memory retrieval"),
            ("speculative_planning", True, "Enable speculative follow-up prediction"),
            ("review_pipeline", True, "Enable quality review after task completion"),
            ("model_routing", True, "Enable intelligent model routing"),
            ("demo_learning", True, "Enable demo recording and replay"),
            ("aci_messaging", True, "Enable agent communication interface"),
            ("dag_planning", True, "Enable DAG-based mission planning"),
            ("dynamic_teams", True, "Enable dynamic team formation"),
            ("event_bus", True, "Enable event bus pub/sub"),
            ("capability_registry", True, "Enable capability registry"),
        ]
        for name, enabled, desc in defaults:
            self._flags[name] = FeatureFlag(name=name, enabled=enabled, description=desc)

    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled."""
        flag = self._flags.get(flag_name)
        return flag.enabled if flag else True  # default to enabled

    def toggle(self, flag_name: str) -> Optional[FeatureFlag]:
        """Toggle a feature flag."""
        flag = self._flags.get(flag_name)
        if flag:
            flag.enabled = not flag.enabled
            flag.toggled_at = time.time()
            logger.info(f"Feature flag '{flag_name}' → {'ON' if flag.enabled else 'OFF'}")
            return flag
        return None

    def set_flag(self, flag_name: str, enabled: bool) -> FeatureFlag:
        """Set a feature flag explicitly."""
        if flag_name not in self._flags:
            self._flags[flag_name] = FeatureFlag(name=flag_name, enabled=enabled)
        else:
            self._flags[flag_name].enabled = enabled
            self._flags[flag_name].toggled_at = time.time()
        return self._flags[flag_name]

    def get_flags(self) -> list[dict]:
        return [f.to_dict() for f in self._flags.values()]

    # === Debug Data ===

    def set_debug(self, key: str, value: Any):
        """Store debug data."""
        self._debug_data[key] = value

    def get_debug(self, key: str = None) -> Any:
        """Get debug data."""
        if key:
            return self._debug_data.get(key)
        return dict(self._debug_data)

    def clear_debug(self):
        self._debug_data.clear()

    # === System Introspection ===

    def get_internal_state(self) -> dict:
        """Get internal state of all subsystems."""
        state = {
            "dev_mode": self._enabled,
            "python_version": sys.version,
            "pid": os.getpid(),
            "flags": self.get_flags(),
        }

        # Event Bus state
        try:
            from jarvis.core.events import event_bus
            state["event_bus"] = event_bus.get_stats()
        except Exception:
            state["event_bus"] = {"error": "not initialized"}

        # Capability Registry state
        try:
            from jarvis.core.capabilities import registry
            state["capabilities"] = {"status": "available"}
        except Exception:
            state["capabilities"] = {"error": "not initialized"}

        # Memory Provider state
        try:
            from jarvis.brain.memory_provider import get_memory
            mem = get_memory()
            state["memory"] = {
                "provider": type(mem).__name__,
                "status": "available",
            }
        except Exception:
            state["memory"] = {"error": "not initialized"}

        return state

    def get_env(self) -> dict:
        """Get relevant environment variables (sanitized)."""
        safe_keys = [
            "JARVIS_DEV_MODE", "VIEW_MODE", "CHAT_MODE",
            "NVIDIA_MODEL", "DB_PATH", "HOST", "PORT",
        ]
        return {k: os.getenv(k, "not set") for k in safe_keys}

    def get_stats(self) -> dict:
        return {
            "dev_mode_enabled": self._enabled,
            "total_flags": len(self._flags),
            "enabled_flags": sum(1 for f in self._flags.values() if f.enabled),
            "debug_entries": len(self._debug_data),
        }


# Module-level singleton
developer_mode = DeveloperMode()
