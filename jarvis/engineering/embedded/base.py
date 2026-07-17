"""Embedded Provider — Abstract base for embedded systems integrations.

Supported platforms: Arduino, ESP32/PlatformIO, Raspberry Pi, STM32, MicroPython
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class Platform(str, Enum):
    ARDUINO = "arduino"
    ESP32 = "esp32"
    RASPBERRY_PI = "raspberry_pi"
    STM32 = "stm32"
    MICROPYTHON = "micropython"
    ESPIDF = "esp_idf"


class BuildStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    COMPILING = "compiling"
    UPLOADING = "uploading"
    UNKNOWN = "unknown"


class EmbeddedProvider(ABC):
    """Abstract base class for embedded systems integrations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name."""
        ...

    @property
    @abstractmethod
    def supported_platforms(self) -> List[Platform]:
        """List of supported embedded platforms."""
        ...

    @abstractmethod
    async def create_project(
        self, name: str, platform: Platform, params: Dict[str, Any]
    ) -> Dict:
        """Create a new embedded project.

        Args:
            name: Project name
            platform: Target platform (Arduino, ESP32, etc.)
            params: Project parameters (board, libraries, etc.)

        Returns:
            Dict with project_id, name, path, platform
        """
        ...

    @abstractmethod
    async def compile(self, project_id: str) -> Dict:
        """Compile firmware.

        Returns:
            Dict with status, binary_path, size, warnings, errors
        """
        ...

    @abstractmethod
    async def upload(self, project_id: str, device: str) -> Dict:
        """Upload firmware to device.

        Args:
            project_id: Project ID
            device: Serial port or device identifier

        Returns:
            Dict with status, device, upload_time
        """
        ...

    @abstractmethod
    async def monitor(
        self, project_id: str, device: str, duration: int = 10
    ) -> Dict:
        """Monitor serial output from device.

        Args:
            project_id: Project ID
            device: Serial port
            duration: Monitoring duration in seconds

        Returns:
            Dict with output lines, timestamps
        """
        ...

    @abstractmethod
    async def list_devices(self) -> List[Dict]:
        """List connected devices.

        Returns:
            List of dicts with port, board, description
        """
        ...

    @abstractmethod
    async def list_boards(self, platform: Optional[Platform] = None) -> List[Dict]:
        """List supported boards.

        Returns:
            List of dicts with fqbn, name, platform
        """
        ...

    @abstractmethod
    async def install_library(self, library: str) -> Dict:
        """Install a library.

        Returns:
            Dict with status, library, version
        """
        ...

    @abstractmethod
    async def list_libraries(self) -> List[Dict]:
        """List installed libraries.

        Returns:
            List of dicts with name, version, author
        """
        ...

    async def generate_pin_map(self, board: str) -> Dict:
        """Generate pin map for a board.

        Returns:
            Dict with pins, capabilities, constraints
        """
        return {"pins": [], "note": "Pin map generation not supported"}

    async def validate_pin_config(
        self, board: str, config: Dict[str, Any]
    ) -> Dict:
        """Validate pin configuration for conflicts.

        Returns:
            Dict with valid, conflicts, warnings
        """
        return {"valid": True, "conflicts": [], "warnings": []}
