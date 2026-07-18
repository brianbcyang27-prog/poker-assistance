"""Plugin data models — manifest, metadata, and type registry."""

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class PluginType(str, enum.Enum):
    """Supported plugin types."""
    TOOL = "tool"
    WORKER = "worker"
    KING = "king"
    MEMORY_PROVIDER = "memory_provider"
    BROWSER_PROVIDER = "browser_provider"
    CAD_PROVIDER = "cad_provider"
    PCB_PROVIDER = "pcb_provider"
    VISION_PROVIDER = "vision_provider"
    LLM_PROVIDER = "llm_provider"
    VOICE_PROVIDER = "voice_provider"
    DEPLOYMENT_PROVIDER = "deployment_provider"


@dataclass
class PluginManifest:
    """Describes a plugin via its plugin.json."""
    name: str
    version: str
    author: str = ""
    description: str = ""
    plugin_type: PluginType = PluginType.TOOL
    entry_point: str = "__init__.py"
    dependencies: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        raw_type = data.get("plugin_type", "tool")
        try:
            ptype = PluginType(raw_type)
        except ValueError:
            ptype = PluginType.TOOL
        return cls(
            name=data["name"],
            version=data.get("version", "0.0.1"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            plugin_type=ptype,
            entry_point=data.get("entry_point", "__init__.py"),
            dependencies=data.get("dependencies", []),
            config_schema=data.get("config_schema", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "plugin_type": self.plugin_type.value,
            "entry_point": self.entry_point,
            "dependencies": self.dependencies,
            "config_schema": self.config_schema,
        }


@dataclass
class Plugin:
    """A loaded or loadable plugin."""
    name: str
    version: str
    author: str = ""
    description: str = ""
    plugin_type: PluginType = PluginType.TOOL
    manifest: Optional[PluginManifest] = None
    module: Any = None
    enabled: bool = True
    loaded_at: Optional[float] = None
