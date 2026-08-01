"""Tool intelligence data models."""

from dataclasses import dataclass, field
from enum import StrEnum


class ToolCategory(StrEnum):
    CAD = "cad"
    PCB = "pcb"
    FIRMWARE = "firmware"
    RENDERING = "rendering"
    VERSION_CONTROL = "version_control"
    CONTAINERIZATION = "containerization"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    DATABASE = "database"
    AI_ML = "ai_ml"
    BROWSER = "browser"
    FILE_SYSTEM = "file_system"
    COMMUNICATION = "communication"


@dataclass
class ToolCapability:
    name: str = ""
    description: str = ""
    input_types: list[str] = field(default_factory=list)
    output_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_types": self.input_types,
            "output_types": self.output_types,
        }


@dataclass
class ToolInfo:
    name: str = ""
    category: str = ""
    description: str = ""
    capabilities: list[ToolCapability] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    common_failures: list[dict[str, str]] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    check_command: str = ""
    install_command: str = ""
    version_command: str = ""
    available: bool = False
    version: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "requirements": self.requirements,
            "common_failures": self.common_failures,
            "examples": self.examples,
            "check_command": self.check_command,
            "install_command": self.install_command,
            "version_command": self.version_command,
            "available": self.available,
            "version": self.version,
        }
