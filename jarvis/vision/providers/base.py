"""Abstract vision provider interface.

Each provider (Ollama, NVIDIA, OpenAI) implements this interface
so JARVIS can use different vision models interchangeably.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.vision.providers")


@dataclass
class DetectedObject:
    """A visual object detected in a screenshot."""
    type: str = ""          # button, menu, icon, text, window, dialog, toolbar, etc.
    name: str = ""          # label/text on the object
    x: int = 0              # center x coordinate
    y: int = 0              # center y coordinate
    width: int = 0          # bounding box width
    height: int = 0         # bounding box height
    confidence: float = 0.0 # 0.0 to 1.0
    description: str = ""   # additional context
    color: str = ""         # dominant color if relevant
    state: str = ""         # enabled/disabled/active/etc.

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": round(self.confidence, 3),
            "description": self.description,
            "color": self.color,
            "state": self.state,
        }

    def center(self) -> tuple:
        return (self.x, self.y)


@dataclass
class VisionResult:
    """Result from a vision provider analysis."""
    application: str = ""           # detected application name
    screen_description: str = ""    # natural language description
    objects: List[DetectedObject] = field(default_factory=list)
    layout: dict = field(default_factory=dict)  # layout structure
    text_content: str = ""          # extracted text
    raw_response: str = ""          # raw model response
    provider: str = ""              # which provider was used
    model: str = ""                 # which model was used
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "application": self.application,
            "screen_description": self.screen_description,
            "objects": [o.to_dict() for o in self.objects],
            "object_count": len(self.objects),
            "layout": self.layout,
            "text_content": self.text_content,
            "provider": self.provider,
            "model": self.model,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
            "error": self.error,
        }

    def find_objects(self, query: str) -> list:
        """Find objects matching a natural language query."""
        query_lower = query.lower()
        return [
            obj for obj in self.objects
            if query_lower in obj.type.lower()
            or query_lower in obj.name.lower()
            or query_lower in obj.description.lower()
            or query_lower in obj.color.lower()
        ]

    def find_best_match(self, query: str) -> Optional[DetectedObject]:
        """Find the single best matching object."""
        matches = self.find_objects(query)
        if not matches:
            return None
        return max(matches, key=lambda o: o.confidence)


class VisionProvider(ABC):
    """Abstract interface for vision model providers.

    Providers send screenshots to vision models and return
    structured analysis of what's on screen.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'ollama', 'nvidia', 'openai')."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Model name (e.g., 'qwen2.5-vl', 'llava')."""
        pass

    @abstractmethod
    async def initialize(self) -> dict:
        """Initialize the provider (connect, verify model availability).

        Returns {"ok": bool, ...}
        """
        pass

    @abstractmethod
    async def analyze_image(
        self,
        image_path: str = "",
        image_base64: str = "",
        prompt: str = "",
    ) -> VisionResult:
        """Analyze an image and return structured understanding.

        Args:
            image_path: Path to image file
            image_base64: Base64-encoded image data (alternative)
            prompt: Analysis prompt

        Returns:
            VisionResult with detected objects and description
        """
        pass

    @abstractmethod
    async def describe_screen(self, image_path: str = "") -> str:
        """Get a natural language description of what's on screen.

        Returns a concise description suitable for LLM context.
        """
        pass

    @abstractmethod
    async def find_in_image(
        self,
        image_path: str = "",
        query: str = "",
    ) -> list:
        """Find specific objects in an image matching a query.

        Returns list of DetectedObject.
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """Check if the provider is available and responsive.

        Returns {"ok": bool, "provider": str, "model": str, ...}
        """
        pass
