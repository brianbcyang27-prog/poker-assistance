"""
Architecture Settings - Configuration and persistence for AI architectures.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ArchitectureSettings:
    """Settings for architecture selection and configuration."""

    # Default architecture (stored as architecture name)
    default_architecture: str = "jarvis_native"

    # Per-architecture configurations
    architecture_configs: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Experimental features
    experimental_mode: bool = False

    # Architecture-specific settings
    auto_save_plans: bool = True
    auto_reflect: bool = True
    verification_required: bool = True
    max_plan_steps: int = 20
    max_execution_time_seconds: int = 300

    # Memory settings
    working_memory_limit: int = 50
    short_term_memory_limit: int = 200
    long_term_memory_limit: int = 1000

    # Voice settings
    voice_feedback: bool = True
    voice_announce_states: bool = True

    # UI settings
    show_thought_stream: bool = True
    show_mission_progress: bool = True
    show_tool_cards: bool = True
    show_reasoning: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "default_architecture": self.default_architecture,
            "architecture_configs": self.architecture_configs,
            "experimental_mode": self.experimental_mode,
            "auto_save_plans": self.auto_save_plans,
            "auto_reflect": self.auto_reflect,
            "verification_required": self.verification_required,
            "max_plan_steps": self.max_plan_steps,
            "max_execution_time_seconds": self.max_execution_time_seconds,
            "working_memory_limit": self.working_memory_limit,
            "short_term_memory_limit": self.short_term_memory_limit,
            "long_term_memory_limit": self.long_term_memory_limit,
            "voice_feedback": self.voice_feedback,
            "voice_announce_states": self.voice_announce_states,
            "show_thought_stream": self.show_thought_stream,
            "show_mission_progress": self.show_mission_progress,
            "show_tool_cards": self.show_tool_cards,
            "show_reasoning": self.show_reasoning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArchitectureSettings":
        """Create from dictionary."""
        return cls(
            default_architecture=data.get("default_architecture", "jarvis_native"),
            architecture_configs=data.get("architecture_configs", {}),
            experimental_mode=data.get("experimental_mode", False),
            auto_save_plans=data.get("auto_save_plans", True),
            auto_reflect=data.get("auto_reflect", True),
            verification_required=data.get("verification_required", True),
            max_plan_steps=data.get("max_plan_steps", 20),
            max_execution_time_seconds=data.get("max_execution_time_seconds", 300),
            working_memory_limit=data.get("working_memory_limit", 50),
            short_term_memory_limit=data.get("short_term_memory_limit", 200),
            long_term_memory_limit=data.get("long_term_memory_limit", 1000),
            voice_feedback=data.get("voice_feedback", True),
            voice_announce_states=data.get("voice_announce_states", True),
            show_thought_stream=data.get("show_thought_stream", True),
            show_mission_progress=data.get("show_mission_progress", True),
            show_tool_cards=data.get("show_tool_cards", True),
            show_reasoning=data.get("show_reasoning", True),
        )


class ArchitectureSettingsManager:
    """Manages persistence of architecture settings."""

    def __init__(self, settings_path: str | None = None):
        if settings_path is None:
            # Default to JARVIS config directory
            base_dir = Path.home() / ".jarvis"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.settings_path = base_dir / "architecture_settings.json"
        else:
            self.settings_path = Path(settings_path)

        self._settings: ArchitectureSettings | None = None

    def load(self) -> ArchitectureSettings:
        """Load settings from file."""
        if self._settings is not None:
            return self._settings

        if self.settings_path.exists():
            try:
                with open(self.settings_path) as f:
                    data = json.load(f)
                self._settings = ArchitectureSettings.from_dict(data)
            except Exception as e:
                print(f"Failed to load architecture settings: {e}")
                self._settings = ArchitectureSettings()
        else:
            self._settings = ArchitectureSettings()

        return self._settings

    def save(self, settings: ArchitectureSettings | None = None) -> bool:
        """Save settings to file."""
        if settings is not None:
            self._settings = settings

        if self._settings is None:
            return False

        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, "w") as f:
                json.dump(self._settings.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Failed to save architecture settings: {e}")
            return False

    def get(self) -> ArchitectureSettings:
        """Get current settings (load if needed)."""
        if self._settings is None:
            return self.load()
        return self._settings

    def update(self, **kwargs) -> ArchitectureSettings:
        """Update specific settings and save."""
        settings = self.get()
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        self.save(settings)
        return settings


# Global settings manager instance
_settings_manager: ArchitectureSettingsManager | None = None


def get_settings_manager() -> ArchitectureSettingsManager:
    """Get the global settings manager."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = ArchitectureSettingsManager()
    return _settings_manager


def get_architecture_config(architecture_name: str) -> dict[str, Any]:
    """Get configuration for a specific architecture."""
    manager = get_settings_manager()
    settings = manager.get()
    return settings.architecture_configs.get(architecture_name, {})


def set_architecture_config(architecture_name: str, config: dict[str, Any]) -> bool:
    """Set configuration for a specific architecture."""
    manager = get_settings_manager()
    settings = manager.get()
    settings.architecture_configs[architecture_name] = config
    return manager.save(settings)
