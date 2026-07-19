"""Agent persona data models."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class AgentRole(str, Enum):
    ARCHITECT = "architect"
    DEVELOPER = "developer"
    TESTER = "tester"
    REVIEWER = "reviewer"
    RESEARCHER = "researcher"
    DESIGNER = "designer"
    DEVOPS = "devops"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    ANALYST = "analyst"


@dataclass
class Persona:
    name: str = ""
    role: str = "developer"
    personality: str = ""
    expertise: List[str] = field(default_factory=list)
    communication_style: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    preferred_tools: List[str] = field(default_factory=list)
    greeting: str = ""
    icon: str = ""
    color: str = ""
    active: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "personality": self.personality,
            "expertise": self.expertise,
            "communication_style": self.communication_style,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "preferred_tools": self.preferred_tools,
            "greeting": self.greeting,
            "icon": self.icon,
            "color": self.color,
            "active": self.active,
        }


@dataclass
class AgentIdentity:
    agent_id: str = ""
    persona: Optional[Persona] = None
    mission_count: int = 0
    success_rate: float = 0.0
    special_achievements: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "persona": self.persona.to_dict() if self.persona else None,
            "mission_count": self.mission_count,
            "success_rate": self.success_rate,
            "special_achievements": self.special_achievements,
        }
